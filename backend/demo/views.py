from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from collections import Counter
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Answer,
    Course,
    CourseEnrollment,
    Exam,
    OperationLog,
    Question,
    QuestionBankItem,
    Submission,
    SystemConfig,
    UserProfile,
)


# 这个文件是后端业务入口：
# - 认证（注册、登录、当前用户）
# - 课程与选课
# - 题库维护
# - 试卷创建、作答、阅卷、统计
# - 管理员能力（用户管理、日志、考试全局控制、系统配置）


@api_view(['GET'])
def hello_world(request):
    """健康检查接口。

    用途：快速验证后端服务是否启动成功。
    """
    return Response({'message': 'Hello from Django!'})


def _get_role(user):
    """读取用户角色。

    角色存储在 UserProfile，而不是 Django 内置 User 表。
    """
    # 角色信息来自 UserProfile 表，而不是 auth_user 表。
    if not hasattr(user, 'profile'):
        return None
    return user.profile.role


def _require_teacher(user):
    """判断当前用户是否老师角色。"""
    role = _get_role(user)
    return role == 'teacher'


def _require_admin(user):
    """判断当前用户是否管理员角色。"""
    role = _get_role(user)
    return role == 'admin'


def _log_operation(request, action, actor=None, target_type='', target_id=None, target_label='', detail=''):
    """记录系统关键操作日志。"""
    ip_addr = ''
    if request is not None:
        ip_addr = str(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') or '')[:64]

    OperationLog.objects.create(
        action=action,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        detail=str(detail or ''),
        ip_address=ip_addr,
    )


def _parse_keywords(raw_text):
    """把关键词字符串标准化为列表（去空格、小写）。"""
    return [item.strip().lower() for item in str(raw_text).split(',') if item.strip()]


def _split_tags(raw_tags):
    """把标签字符串拆成列表，用于筛选与统计。"""
    return [item.strip() for item in str(raw_tags).split(',') if item.strip()]


def _grade_subjective(answer_text, keywords, full_score):
    """主观题关键词打分策略。

    返回值：(score_awarded, is_correct, feedback_text)
    - score_awarded: 实际给分
    - is_correct: 是否视为满分正确
    - feedback_text: 给前端展示的评分说明
    """
    # 主观题自动阅卷策略：按关键词命中比例分段给分。
    if not answer_text:
        return 0, False, '未作答'

    if not keywords:
        return full_score, True, '未设置关键词，按满分计'

    text = answer_text.lower()
    hit = sum(1 for kw in keywords if kw in text)
    ratio = hit / len(keywords)

    if ratio >= 1:
        return full_score, True, f'关键词命中 {hit}/{len(keywords)}'
    if ratio >= 0.6:
        return int(full_score * 0.8), False, f'关键词命中 {hit}/{len(keywords)}'
    if ratio >= 0.3:
        return int(full_score * 0.5), False, f'关键词命中 {hit}/{len(keywords)}'
    return 0, False, f'关键词命中 {hit}/{len(keywords)}'


def _validate_single_question_payload(item):
    """校验单选题输入结构并返回标准化字段。"""
    option_list = item.get('options', [])
    if not isinstance(option_list, list) or len(option_list) != 4:
        return None, 'single 题型必须提供 4 个选项'

    for opt in option_list:
        if not str(opt).strip():
            return None, 'single 题型选项不能为空'

    try:
        correct_option = int(item.get('correct_option', -1))
    except (TypeError, ValueError):
        return None, 'correct_option 必须是数字'

    if correct_option < 0 or correct_option > 3:
        return None, 'correct_option 必须在 0~3'

    payload = {
        'option_a': str(option_list[0]).strip(),
        'option_b': str(option_list[1]).strip(),
        'option_c': str(option_list[2]).strip(),
        'option_d': str(option_list[3]).strip(),
        'correct_option': correct_option,
        'reference_answer': '',
        'keyword_answers': '',
    }
    return payload, None


def _validate_subjective_question_payload(item):
    """校验主观题输入结构并返回标准化字段。"""
    reference_answer = str(item.get('reference_answer', '')).strip()
    keyword_answers = str(item.get('keyword_answers', '')).strip()
    payload = {
        'option_a': '',
        'option_b': '',
        'option_c': '',
        'option_d': '',
        'correct_option': None,
        'reference_answer': reference_answer,
        'keyword_answers': keyword_answers,
    }
    return payload, None


def _normalize_question_payload(item):
    """统一题目入参结构。

    该函数是题库创建、试卷创建的公共入口，保证数据格式一致。
    """
    # 将前端上传的题目统一标准化，便于同时写入题库/试卷。
    question_type = str(item.get('question_type', 'single')).strip()
    text = str(item.get('text', '')).strip()

    try:
        score = int(item.get('score', 10))
    except (TypeError, ValueError):
        return None, 'score 必须是数字'

    if score <= 0:
        return None, 'score 必须大于 0'
    if not text:
        return None, '题干不能为空'
    if question_type not in ('single', 'subjective'):
        return None, 'question_type 必须是 single 或 subjective'

    extra_payload, error = (
        _validate_single_question_payload(item)
        if question_type == 'single'
        else _validate_subjective_question_payload(item)
    )
    if error:
        return None, error

    data = {
        'question_type': question_type,
        'text': text,
        'score': score,
    }
    data.update(extra_payload)

    subject_tag = str(item.get('subject_tag', 'common')).strip() or 'common'
    raw_tags = str(item.get('tags', '')).strip()
    tags = ','.join([x.strip() for x in raw_tags.split(',') if x.strip()])
    if not tags:
        return None, '至少需要一个标签'
    try:
        difficulty = int(item.get('difficulty', 3))
    except (TypeError, ValueError):
        return None, 'difficulty 必须是数字'

    if difficulty < 1 or difficulty > 5:
        return None, 'difficulty 必须在 1~5'

    data['subject_tag'] = subject_tag
    data['tags'] = tags
    data['difficulty'] = difficulty
    return data, None


def _question_to_dict(question, include_answer=False):
    """把 Question 模型序列化为前端可消费的字典。"""
    payload = {
        'id': question.id,
        'question_type': question.question_type,
        'text': question.text,
        'score': question.score,
    }

    if question.question_type == 'single':
        payload['options'] = [question.option_a, question.option_b, question.option_c, question.option_d]
        if include_answer:
            payload['correct_option'] = question.correct_option
    else:
        payload['reference_answer'] = question.reference_answer if include_answer else ''
        payload['keyword_answers'] = question.keyword_answers if include_answer else ''

    return payload


def _exam_to_dict(exam, include_questions=False, include_answer=False, attempted=False):
    """把试卷对象序列化为接口响应。

    include_questions=True 时返回题目列表。
    include_answer=True 时返回标准答案字段（仅老师端可用）。
    """
    has_subjective = exam.questions.filter(question_type='subjective').exists()
    payload = {
        'id': exam.id,
        'title': exam.title,
        'description': exam.description,
        'duration_minutes': exam.duration_minutes,
        'is_published': exam.is_published,
        'result_policy': exam.result_policy,
        'control_status': exam.control_status,
        'has_subjective': has_subjective,
        'created_by': exam.created_by.username,
        'created_at': exam.created_at,
        'question_count': exam.questions.count(),
        'attempted': attempted,
        'course': (
            {
                'id': exam.course.id,
                'name': exam.course.name,
                'subject_tag': exam.course.subject_tag,
            }
            if exam.course
            else None
        ),
    }
    if include_questions:
        payload['questions'] = [
            _question_to_dict(question, include_answer=include_answer)
            for question in exam.questions.all().order_by('id')
        ]
    return payload


def _bank_item_to_dict(item):
    """把题库题对象序列化为前端字典结构。"""
    return {
        'id': item.id,
        'teacher_id': item.teacher_id,
        'teacher_username': item.teacher.username,
        'subject_tag': item.subject_tag,
        'tags': item.tags,
        'difficulty': item.difficulty,
        'question_type': item.question_type,
        'text': item.text,
        'options': [item.option_a, item.option_b, item.option_c, item.option_d],
        'correct_option': item.correct_option,
        'reference_answer': item.reference_answer,
        'keyword_answers': item.keyword_answers,
        'score': item.score,
        'updated_at': item.updated_at,
    }


@api_view(['POST'])
def auth_register(request):
    """注册接口。

    写入 auth_user + demo_userprofile + authtoken_token 三张表。
    """
    # 注册时会写入两张表：
    # 1) auth_user（用户名、密码哈希）
    # 2) demo_userprofile（角色）
    # 同时生成 token（authtoken_token 表），供前端后续携带认证。
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    role = request.data.get('role', '').strip()

    if role not in ('admin', 'student', 'teacher'):
        return Response({'error': 'role must be admin or student or teacher'}, status=400)
    if role == 'admin' and UserProfile.objects.filter(role='admin').exists():
        return Response({'error': 'admin registration is disabled'}, status=403)
    if len(username) < 3:
        return Response({'error': 'username must be at least 3 chars'}, status=400)
    if len(password) < 6:
        return Response({'error': 'password must be at least 6 chars'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'username already exists'}, status=400)

    with transaction.atomic():
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user, role=role)
        token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {
            'token': token.key,
            'user': {'id': user.id, 'username': user.username, 'role': role},
        },
        status=201,
    )


@api_view(['POST'])
def auth_login(request):
    """登录接口，返回 token 和用户角色。"""
    # 登录成功后返回 token + 用户角色。
    # 前端会把 token 存在浏览器 localStorage，并在每次请求头带上它。
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'invalid username or password'}, status=400)

    if not hasattr(user, 'profile'):
        return Response({'error': 'profile missing, please contact admin'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    _log_operation(
        request,
        action='user_login',
        actor=user,
        target_type='user',
        target_id=user.id,
        target_label=user.username,
        detail='login success',
    )
    return Response(
        {
            'token': token.key,
            'user': {'id': user.id, 'username': user.username, 'role': user.profile.role},
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    """当前登录用户信息接口。"""
    role = _get_role(request.user)
    if not role:
        return Response({'error': 'profile missing'}, status=400)
    return Response({'id': request.user.id, 'username': request.user.username, 'role': role})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def students(request):
    """老师查询学生列表接口，支持 q 模糊搜索。"""
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can query students'}, status=403)

    q = str(request.query_params.get('q', '')).strip()
    queryset = User.objects.filter(profile__role='student').order_by('username')
    if q:
        queryset = queryset.filter(username__icontains=q)

    data = [{'id': user.id, 'username': user.username} for user in queryset[:50]]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def question_bank_meta(request):
    """题库元数据接口。

    返回科目候选值和热门标签，供前端筛选器初始化。
    """
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can view question-bank meta'}, status=403)

    subject_tags = {'common'}
    for tag in Course.objects.values_list('subject_tag', flat=True):
        if tag:
            subject_tags.add(tag)

    tag_counter = Counter()
    for raw_tags in QuestionBankItem.objects.values_list('tags', flat=True):
        for tag in _split_tags(raw_tags):
            tag_counter[tag] += 1

    return Response(
        {
            'subject_options': sorted(subject_tags),
            'hot_tags': [{'tag': k, 'count': v} for k, v in tag_counter.most_common(15)],
        }
    )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def courses(request):
    """课程接口。

    POST: 老师创建课程
    GET: 老师看自己课程 / 学生看自己已加入课程
    """
    # 课程接口：
    # - 老师：创建课程、查看自己课程
    # - 学生：查看自己已加入课程
    role = _get_role(request.user)

    if request.method == 'POST':
        if role != 'teacher':
            return Response({'error': 'only teacher can create courses'}, status=403)

        name = str(request.data.get('name', '')).strip()
        subject_tag = str(request.data.get('subject_tag', 'common')).strip() or 'common'
        description = str(request.data.get('description', '')).strip()
        if not name:
            return Response({'error': 'course name is required'}, status=400)

        course = Course.objects.create(
            name=name,
            subject_tag=subject_tag,
            description=description,
            teacher=request.user,
        )
        return Response(
            {
                'id': course.id,
                'name': course.name,
                'subject_tag': course.subject_tag,
                'description': course.description,
            },
            status=201,
        )

    if role == 'teacher':
        queryset = Course.objects.filter(teacher=request.user).order_by('-created_at')
        return Response(
            [
                {
                    'id': course.id,
                    'name': course.name,
                    'subject_tag': course.subject_tag,
                    'description': course.description,
                    'student_count': course.enrollments.count(),
                }
                for course in queryset
            ]
        )

    queryset = Course.objects.filter(enrollments__student=request.user).distinct().order_by('-created_at')
    return Response(
        [
            {
                'id': course.id,
                'name': course.name,
                'subject_tag': course.subject_tag,
                'description': course.description,
                'teacher': course.teacher.username,
            }
            for course in queryset
        ]
    )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def course_students(request, course_id):
    """课程学生管理接口。

    GET: 查看课程学生
    POST: add/remove 学生（支持 usernames 批量）
    """
    # 课程学生管理：按用户名 add/remove 选课关系。
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can manage students'}, status=403)

    course = get_object_or_404(Course, id=course_id, teacher=request.user)

    if request.method == 'POST':
        action = str(request.data.get('action', 'add')).strip()
        usernames = request.data.get('usernames')

        if isinstance(usernames, list) and usernames:
            targets = [str(name).strip() for name in usernames if str(name).strip()]
        else:
            username = str(request.data.get('username', '')).strip()
            if not username:
                return Response({'error': 'username is required'}, status=400)
            targets = [username]

        for username in targets:
            student = User.objects.filter(username=username).first()
            if not student or _get_role(student) != 'student':
                continue

            if action == 'remove':
                CourseEnrollment.objects.filter(course=course, student=student).delete()
            else:
                CourseEnrollment.objects.get_or_create(course=course, student=student)

    students = [
        {'id': enrollment.student.id, 'username': enrollment.student.username}
        for enrollment in course.enrollments.select_related('student').all().order_by('-id')
    ]
    return Response({'course': {'id': course.id, 'name': course.name}, 'students': students})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_stats(request, course_id):
    """课程统计接口，返回按试卷和按学生两个统计维度。"""
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can view stats'}, status=403)

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    exams = Exam.objects.filter(course=course).order_by('-created_at')

    exam_stats = []
    for exam in exams:
        agg = exam.submissions.aggregate(avg_score=Avg('total_score'))
        exam_stats.append(
            {
                'exam_id': exam.id,
                'exam_title': exam.title,
                'submission_count': exam.submissions.count(),
                'avg_score': round(float(agg['avg_score'] or 0), 2),
            }
        )

    student_stats = []
    for enrollment in course.enrollments.select_related('student').all():
        student_submissions = Submission.objects.filter(student=enrollment.student, exam__course=course)
        agg = student_submissions.aggregate(avg_score=Avg('total_score'))
        student_stats.append(
            {
                'student_id': enrollment.student.id,
                'student_username': enrollment.student.username,
                'submission_count': student_submissions.count(),
                'avg_score': round(float(agg['avg_score'] or 0), 2),
            }
        )

    return Response(
        {
            'course': {'id': course.id, 'name': course.name},
            'exam_stats': exam_stats,
            'student_stats': student_stats,
        }
    )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def question_bank(request):
    """题库列表/创建接口。"""
    # 题库接口：
    # - POST 新建题库题
    # - GET 查询当前老师的题库题
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can manage question bank'}, status=403)

    if request.method == 'POST':
        payload, error = _normalize_question_payload(request.data)
        if error:
            return Response({'error': error}, status=400)

        item = QuestionBankItem.objects.create(teacher=request.user, **payload)
        return Response(_bank_item_to_dict(item), status=201)

    # 题库共享：所有老师均可查看和选用。
    queryset = QuestionBankItem.objects.select_related('teacher').all().order_by('-updated_at')

    q = str(request.query_params.get('q', '')).strip()
    subject_tag = str(request.query_params.get('subject_tag', '')).strip()
    tag = str(request.query_params.get('tag', '')).strip()
    question_type = str(request.query_params.get('question_type', '')).strip()
    difficulty = str(request.query_params.get('difficulty', '')).strip()

    if q:
        queryset = queryset.filter(text__icontains=q)
    if subject_tag:
        queryset = queryset.filter(subject_tag__iexact=subject_tag)
    if tag:
        queryset = queryset.filter(tags__icontains=tag)
    if question_type in ('single', 'subjective'):
        queryset = queryset.filter(question_type=question_type)
    if difficulty:
        try:
            diff_num = int(difficulty)
            queryset = queryset.filter(difficulty=diff_num)
        except ValueError:
            pass

    return Response([_bank_item_to_dict(item) for item in queryset])


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def question_bank_detail(request, item_id):
    """题库单题编辑/删除接口。

    共享题库可读可用，但只有创建者可改删。
    """
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can manage question bank'}, status=403)

    item = get_object_or_404(QuestionBankItem, id=item_id)

    # 共享题库下，编辑/删除仅允许创建者执行。
    if item.teacher_id != request.user.id:
        return Response({'error': 'only creator can edit or delete this item'}, status=403)

    if request.method == 'DELETE':
        item.delete()
        return Response({'ok': True})

    payload, error = _normalize_question_payload(request.data)
    if error:
        return Response({'error': error}, status=400)

    for key, value in payload.items():
        setattr(item, key, value)
    item.save()
    return Response(_bank_item_to_dict(item))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def exams(request):
    """试卷集合接口。

    POST: 老师创建试卷
    GET: 老师看自己试卷 / 学生看可参加试卷
    """
    role = _get_role(request.user)
    if role not in ('admin', 'student', 'teacher'):
        return Response({'error': 'invalid role'}, status=403)

    if request.method == 'POST':
        # 出卷支持两种来源：
        # 1) bank_item_id：从题库直接引用
        # 2) 题目详情：新题创建，可选 save_to_bank 同步入题库
        if role != 'teacher':
            return Response({'error': 'only teacher can create exams'}, status=403)

        title = str(request.data.get('title', '')).strip()
        description = str(request.data.get('description', '')).strip()
        questions = request.data.get('questions', [])
        course_id = request.data.get('course_id')
        result_policy = str(request.data.get('result_policy', 'teacher_release')).strip()

        try:
            duration_minutes = int(request.data.get('duration_minutes', 60))
        except (TypeError, ValueError):
            return Response({'error': 'duration_minutes must be a number'}, status=400)

        is_published = bool(request.data.get('is_published', True))

        if result_policy not in ('teacher_release', 'auto_release'):
            return Response({'error': 'result_policy must be teacher_release or auto_release'}, status=400)

        if not title:
            return Response({'error': 'title is required'}, status=400)
        if duration_minutes <= 0:
            return Response({'error': 'duration_minutes must be > 0'}, status=400)
        if not isinstance(questions, list) or len(questions) == 0:
            return Response({'error': 'at least one question is required'}, status=400)

        course = None
        if course_id not in (None, '', 'null'):
            course = Course.objects.filter(id=course_id, teacher=request.user).first()
            if not course:
                return Response({'error': 'course not found'}, status=404)

        with transaction.atomic():
            exam = Exam.objects.create(
                title=title,
                description=description,
                duration_minutes=duration_minutes,
                is_published=is_published,
                result_policy=result_policy,
                course=course,
                created_by=request.user,
            )

            has_subjective_question = False

            for item in questions:
                save_to_bank = bool(item.get('save_to_bank', False))
                bank_item = None

                bank_item_id = item.get('bank_item_id')
                if bank_item_id:
                    bank_item = QuestionBankItem.objects.filter(id=bank_item_id).first()
                    if not bank_item:
                        transaction.set_rollback(True)
                        return Response({'error': f'bank item {bank_item_id} not found'}, status=404)
                    if bank_item.question_type == 'subjective':
                        has_subjective_question = True
                    normalized = {
                        'question_type': bank_item.question_type,
                        'text': bank_item.text,
                        'option_a': bank_item.option_a,
                        'option_b': bank_item.option_b,
                        'option_c': bank_item.option_c,
                        'option_d': bank_item.option_d,
                        'correct_option': bank_item.correct_option,
                        'reference_answer': bank_item.reference_answer,
                        'keyword_answers': bank_item.keyword_answers,
                        'score': bank_item.score,
                        'subject_tag': bank_item.subject_tag,
                        'tags': bank_item.tags,
                        'difficulty': bank_item.difficulty,
                    }
                else:
                    normalized, error = _normalize_question_payload(item)
                    if error:
                        transaction.set_rollback(True)
                        return Response({'error': error}, status=400)

                    if normalized['question_type'] == 'subjective':
                        has_subjective_question = True

                    if save_to_bank:
                        bank_payload = {
                            'question_type': normalized['question_type'],
                            'text': normalized['text'],
                            'option_a': normalized['option_a'],
                            'option_b': normalized['option_b'],
                            'option_c': normalized['option_c'],
                            'option_d': normalized['option_d'],
                            'correct_option': normalized['correct_option'],
                            'reference_answer': normalized['reference_answer'],
                            'keyword_answers': normalized['keyword_answers'],
                            'score': normalized['score'],
                            'subject_tag': normalized['subject_tag'],
                            'tags': normalized['tags'],
                            'difficulty': normalized['difficulty'],
                        }
                        bank_item = QuestionBankItem.objects.create(teacher=request.user, **bank_payload)

                question_payload = {
                    'question_type': normalized['question_type'],
                    'text': normalized['text'],
                    'option_a': normalized['option_a'],
                    'option_b': normalized['option_b'],
                    'option_c': normalized['option_c'],
                    'option_d': normalized['option_d'],
                    'correct_option': normalized['correct_option'],
                    'reference_answer': normalized['reference_answer'],
                    'keyword_answers': normalized['keyword_answers'],
                    'score': normalized['score'],
                }

                Question.objects.create(exam=exam, bank_item=bank_item, **question_payload)

            if has_subjective_question and exam.result_policy == 'auto_release':
                exam.result_policy = 'teacher_release'
                exam.save(update_fields=['result_policy'])

            _log_operation(
                request,
                action='exam_publish' if exam.is_published else 'exam_create_draft',
                actor=request.user,
                target_type='exam',
                target_id=exam.id,
                target_label=exam.title,
                detail=f"question_count={exam.questions.count()} result_policy={exam.result_policy}",
            )

        return Response(_exam_to_dict(exam, include_questions=True, include_answer=True), status=201)

    if role == 'teacher':
        queryset = Exam.objects.filter(created_by=request.user).order_by('-created_at')
        return Response([_exam_to_dict(exam) for exam in queryset])

    if role == 'admin':
        queryset = Exam.objects.select_related('course', 'created_by').all().order_by('-created_at')
        return Response([_exam_to_dict(exam) for exam in queryset])

    queryset = (
        Exam.objects.filter(is_published=True)
        .filter(Q(course__isnull=True) | Q(course__enrollments__student=request.user))
        .distinct()
        .order_by('-created_at')
    )
    attempted_exam_ids = set(
        Submission.objects.filter(student=request.user).values_list('exam_id', flat=True)
    )
    return Response([_exam_to_dict(exam, attempted=(exam.id in attempted_exam_ids)) for exam in queryset])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_detail(request, exam_id):
    """试卷详情接口。

    老师可看答案，学生只能看题目（防止泄题）。
    """
    # 学生查看试卷时：
    # - 不返回客观题正确答案
    # - 若试卷绑定课程，则必须在课程里才能看见
    exam = get_object_or_404(Exam, id=exam_id)
    role = _get_role(request.user)

    if role == 'teacher':
        if exam.created_by_id != request.user.id:
            return Response({'error': 'forbidden'}, status=403)
        return Response(_exam_to_dict(exam, include_questions=True, include_answer=True))

    if role == 'student':
        if not exam.is_published:
            return Response({'error': 'exam not published'}, status=403)

        if exam.course and not CourseEnrollment.objects.filter(course=exam.course, student=request.user).exists():
            return Response({'error': 'exam not assigned to your courses'}, status=403)

        attempted = Submission.objects.filter(exam=exam, student=request.user).exists()
        return Response(_exam_to_dict(exam, include_questions=True, attempted=attempted))

    return Response({'error': 'invalid role'}, status=403)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_exam(request, exam_id):
    """交卷接口。

    负责写入 Submission 和 Answer，并根据题型更新状态：
    - 纯客观题可直接 graded
    - 含主观题则 submitted，等待老师批阅
    """
    # 提交试卷后会写入：
    # 1) Submission（一次交卷记录）
    # 2) Answer（每一题的作答与得分）
    # 客观题按正确选项判分，主观题按关键词自动评分。
    if _get_role(request.user) != 'student':
        return Response({'error': 'only student can submit'}, status=403)

    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

    if exam.control_status == 'paused':
        return Response({'error': 'exam is paused by admin'}, status=403)
    if exam.control_status == 'ended':
        return Response({'error': 'exam has been ended by admin'}, status=403)

    if exam.course and not CourseEnrollment.objects.filter(course=exam.course, student=request.user).exists():
        return Response({'error': 'exam not assigned to your courses'}, status=403)

    if Submission.objects.filter(exam=exam, student=request.user).exists():
        return Response({'error': 'you have already submitted this exam'}, status=400)

    answers = request.data.get('answers', {})
    if not isinstance(answers, dict):
        return Response({'error': 'answers must be an object'}, status=400)

    total_score = 0
    max_score = 0
    details = []
    has_subjective = False

    with transaction.atomic():
        submission = Submission.objects.create(exam=exam, student=request.user)

        for question in exam.questions.all().order_by('id'):
            max_score += question.score
            selected = answers.get(str(question.id))
            if selected is None:
                selected = answers.get(question.id)

            score_awarded = 0
            is_correct = False
            selected_option = None
            subjective_answer = ''
            auto_feedback = ''

            if question.question_type == 'single':
                if selected is not None:
                    try:
                        selected_option = int(selected)
                    except (TypeError, ValueError):
                        return Response({'error': f'invalid selected option for question {question.id}'}, status=400)

                    if selected_option < 0 or selected_option > 3:
                        return Response({'error': f'selected option must be 0~3 for question {question.id}'}, status=400)

                    is_correct = selected_option == question.correct_option
                    score_awarded = question.score if is_correct else 0
                    auto_feedback = '客观题自动判分'
            else:
                has_subjective = True
                subjective_answer = str(selected or '').strip()
                score_awarded = 0
                is_correct = False
                auto_feedback = '待老师阅卷'

            Answer.objects.create(
                submission=submission,
                question=question,
                selected_option=selected_option,
                subjective_answer=subjective_answer,
                is_manual_graded=(question.question_type == 'single'),
                is_correct=is_correct,
                score_awarded=score_awarded,
                auto_feedback=auto_feedback,
            )

            total_score += score_awarded
            details.append(
                {
                    'question_id': question.id,
                    'question_type': question.question_type,
                    'selected_option': selected_option,
                    'subjective_answer': subjective_answer,
                    'correct_option': question.correct_option,
                    'score_awarded': score_awarded,
                    'full_score': question.score,
                    'auto_feedback': auto_feedback,
                }
            )

        submission.total_score = total_score
        submission.max_score = max_score
        if has_subjective:
            submission.status = 'submitted'
            submission.is_result_published = False
            submission.published_at = None
        else:
            submission.status = 'graded'
            if exam.result_policy == 'auto_release':
                submission.is_result_published = True
                submission.published_at = timezone.now()

        submission.save(
            update_fields=['total_score', 'max_score', 'status', 'is_result_published', 'published_at', 'graded_at']
        )

    payload = {
        'submission_id': submission.id,
        'status': submission.status,
        'is_result_published': submission.is_result_published,
        'details': details,
        'message': '已提交，等待老师阅卷/发布成绩' if not submission.is_result_published else '已提交并发布成绩',
    }
    if submission.is_result_published:
        payload['total_score'] = total_score
        payload['max_score'] = max_score

    _log_operation(
        request,
        action='answer_submit',
        actor=request.user,
        target_type='exam',
        target_id=exam.id,
        target_label=exam.title,
        detail=f"submission_id={submission.id}",
    )

    return Response(payload, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_grading_overview(request, exam_id):
    """阅卷总览接口。

    返回提交列表 + 未提交学生列表，用于老师批阅首页。
    """
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can view grading overview'}, status=403)

    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)

    submissions = []
    for item in exam.submissions.select_related('student').all().order_by('-submitted_at'):
        submissions.append(
            {
                'submission_id': item.id,
                'student_id': item.student.id,
                'student_username': item.student.username,
                'status': item.status,
                'is_result_published': item.is_result_published,
                'total_score': item.total_score,
                'max_score': item.max_score,
                'submitted_at': item.submitted_at,
            }
        )

    missing_students = []
    if exam.course:
        submitted_student_ids = set(exam.submissions.values_list('student_id', flat=True))
        for enrollment in exam.course.enrollments.select_related('student').all():
            if enrollment.student_id not in submitted_student_ids:
                missing_students.append(
                    {
                        'student_id': enrollment.student_id,
                        'student_username': enrollment.student.username,
                    }
                )

    return Response(
        {
            'exam': _exam_to_dict(exam),
            'submissions': submissions,
            'missing_students': missing_students,
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grade_submission(request, submission_id):
    """单份试卷阅卷接口。

    只处理主观题分数，客观题保持自动判分结果。
    """
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can grade'}, status=403)

    submission = get_object_or_404(Submission.objects.select_related('exam'), id=submission_id)
    if submission.exam.created_by_id != request.user.id:
        return Response({'error': 'forbidden'}, status=403)

    subjective_scores = request.data.get('subjective_scores', {})
    if not isinstance(subjective_scores, dict):
        return Response({'error': 'subjective_scores must be an object'}, status=400)

    with transaction.atomic():
        total_score = 0
        max_score = 0
        for ans in submission.answers.select_related('question').all().order_by('id'):
            question = ans.question
            max_score += question.score

            if question.question_type == 'subjective':
                raw = subjective_scores.get(str(question.id))
                if raw is None:
                    raw = subjective_scores.get(question.id)
                if raw is None:
                    score = 0
                else:
                    try:
                        score = int(raw)
                    except (TypeError, ValueError):
                        return Response({'error': f'invalid score for question {question.id}'}, status=400)

                score = max(0, min(score, question.score))
                ans.score_awarded = score
                ans.is_manual_graded = True
                ans.is_correct = score == question.score
                ans.auto_feedback = '老师已阅卷'
                ans.save(update_fields=['score_awarded', 'is_manual_graded', 'is_correct', 'auto_feedback'])

            total_score += ans.score_awarded

        submission.total_score = total_score
        submission.max_score = max_score
        submission.status = 'graded'
        submission.save(update_fields=['total_score', 'max_score', 'status', 'graded_at'])

    return Response(
        {
            'submission_id': submission.id,
            'status': submission.status,
            'total_score': submission.total_score,
            'max_score': submission.max_score,
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_exam_results(request, exam_id):
    """发布成绩接口。

    仅发布已 graded 且尚未发布的提交。
    """
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can release results'}, status=403)

    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)

    updated = 0
    now = timezone.now()
    for submission in exam.submissions.filter(status='graded', is_result_published=False):
        submission.is_result_published = True
        submission.published_at = now
        submission.save(update_fields=['is_result_published', 'published_at'])
        updated += 1

    return Response({'released_count': updated})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_submissions(request, exam_id):
    """试卷提交详情接口（老师端）。

    返回每份提交的题目作答明细：
    - 单选题：学生选项 + 标准选项
    - 主观题：学生答案 + 标准答案
    """
    if not _require_teacher(request.user):
        return Response({'error': 'only teacher can view submissions'}, status=403)

    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    question_order_map = {
        q.id: idx + 1 for idx, q in enumerate(exam.questions.all().order_by('id'))
    }
    records = []
    for item in exam.submissions.select_related('student').all().order_by('-submitted_at'):
        answer_details = [
            {
                'question_no': question_order_map.get(ans.question_id, 0),
                'question_id': ans.question_id,
                'question_type': ans.question.question_type,
                'selected_option': ans.selected_option,
                'correct_option': ans.question.correct_option,
                'subjective_answer': ans.subjective_answer,
                'reference_answer': ans.question.reference_answer,
                'full_score': ans.question.score,
                'score_awarded': ans.score_awarded,
                'auto_feedback': ans.auto_feedback,
            }
            for ans in item.answers.select_related('question').all().order_by('id')
        ]
        records.append(
            {
                'submission_id': item.id,
                'student_id': item.student.id,
                'student_username': item.student.username,
                'status': item.status,
                'is_result_published': item.is_result_published,
                'total_score': item.total_score,
                'max_score': item.max_score,
                'submitted_at': item.submitted_at,
                'answers': answer_details,
            }
        )

    return Response({'exam': {'id': exam.id, 'title': exam.title}, 'submissions': records})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_users(request):
    """管理员用户管理：查询、创建用户。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can manage users'}, status=403)

    if request.method == 'POST':
        username = str(request.data.get('username', '')).strip()
        password = str(request.data.get('password', '')).strip()
        role = str(request.data.get('role', '')).strip()
        is_active = bool(request.data.get('is_active', True))

        if role not in ('admin', 'teacher', 'student'):
            return Response({'error': 'role must be admin/teacher/student'}, status=400)
        if len(username) < 3:
            return Response({'error': 'username must be at least 3 chars'}, status=400)
        if len(password) < 6:
            return Response({'error': 'password must be at least 6 chars'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'username already exists'}, status=400)

        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password, is_active=is_active)
            UserProfile.objects.create(user=user, role=role)
            Token.objects.get_or_create(user=user)

        _log_operation(
            request,
            action='admin_create_user',
            actor=request.user,
            target_type='user',
            target_id=user.id,
            target_label=user.username,
            detail=f"role={role} is_active={is_active}",
        )

        return Response(
            {
                'id': user.id,
                'username': user.username,
                'role': role,
                'is_active': user.is_active,
            },
            status=201,
        )

    q = str(request.query_params.get('q', '')).strip()
    role = str(request.query_params.get('role', '')).strip()
    queryset = User.objects.select_related('profile').all().order_by('id')
    if q:
        queryset = queryset.filter(username__icontains=q)
    if role in ('admin', 'teacher', 'student'):
        queryset = queryset.filter(profile__role=role)

    data = [
        {
            'id': user.id,
            'username': user.username,
            'role': user.profile.role if hasattr(user, 'profile') else '',
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined,
        }
        for user in queryset[:200]
    ]
    return Response(data)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_user_detail(request, user_id):
    """管理员用户管理：编辑、删除（可用于禁用账号）。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can manage users'}, status=403)

    user = get_object_or_404(User, id=user_id)

    if user.id == request.user.id:
        return Response({'error': 'admin cannot operate on own account'}, status=400)

    if request.method == 'DELETE':
        username = user.username
        user.delete()
        _log_operation(
            request,
            action='admin_delete_user',
            actor=request.user,
            target_type='user',
            target_id=user_id,
            target_label=username,
        )
        return Response({'ok': True})

    username = request.data.get('username')
    role = request.data.get('role')
    is_active = request.data.get('is_active')

    if username is not None:
        username = str(username).strip()
        if len(username) < 3:
            return Response({'error': 'username must be at least 3 chars'}, status=400)
        if User.objects.exclude(id=user.id).filter(username=username).exists():
            return Response({'error': 'username already exists'}, status=400)
        user.username = username

    if is_active is not None:
        user.is_active = bool(is_active)

    if role is not None:
        role = str(role).strip()
        if role not in ('admin', 'teacher', 'student'):
            return Response({'error': 'role must be admin/teacher/student'}, status=400)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save(update_fields=['role'])

    user.save()

    _log_operation(
        request,
        action='admin_update_user',
        actor=request.user,
        target_type='user',
        target_id=user.id,
        target_label=user.username,
        detail=f"role={user.profile.role if hasattr(user, 'profile') else ''} is_active={user.is_active}",
    )

    return Response(
        {
            'id': user.id,
            'username': user.username,
            'role': user.profile.role if hasattr(user, 'profile') else '',
            'is_active': user.is_active,
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_reset_user_password(request, user_id):
    """管理员重置指定用户密码。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can reset password'}, status=403)

    user = get_object_or_404(User, id=user_id)
    if user.id == request.user.id:
        return Response({'error': 'admin cannot operate on own account'}, status=400)
    new_password = str(request.data.get('new_password', '')).strip()
    if len(new_password) < 6:
        return Response({'error': 'new_password must be at least 6 chars'}, status=400)

    user.set_password(new_password)
    user.save(update_fields=['password'])
    Token.objects.filter(user=user).delete()
    Token.objects.get_or_create(user=user)

    _log_operation(
        request,
        action='admin_reset_password',
        actor=request.user,
        target_type='user',
        target_id=user.id,
        target_label=user.username,
    )
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_change_own_password(request):
    """管理员修改自己的密码（独立页面使用）。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can change own password here'}, status=403)

    old_password = str(request.data.get('old_password', '')).strip()
    new_password = str(request.data.get('new_password', '')).strip()

    if len(new_password) < 6:
        return Response({'error': 'new_password must be at least 6 chars'}, status=400)
    if old_password == new_password:
        return Response({'error': 'new password must be different from old password'}, status=400)
    if not request.user.check_password(old_password):
        return Response({'error': 'old_password is incorrect'}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])

    Token.objects.filter(user=request.user).delete()
    token, _ = Token.objects.get_or_create(user=request.user)

    _log_operation(
        request,
        action='admin_change_own_password',
        actor=request.user,
        target_type='user',
        target_id=request.user.id,
        target_label=request.user.username,
    )

    return Response(
        {
            'token': token.key,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'role': request.user.profile.role if hasattr(request.user, 'profile') else 'admin',
            },
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_operation_logs(request):
    """管理员查看系统关键操作日志。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can view logs'}, status=403)

    action = str(request.query_params.get('action', '')).strip()
    q = str(request.query_params.get('q', '')).strip()
    limit_raw = request.query_params.get('limit', 100)
    try:
        limit = max(1, min(int(limit_raw), 500))
    except (TypeError, ValueError):
        limit = 100

    queryset = OperationLog.objects.select_related('actor').all().order_by('-created_at')
    if action:
        queryset = queryset.filter(action__icontains=action)
    if q:
        queryset = queryset.filter(Q(target_label__icontains=q) | Q(detail__icontains=q) | Q(actor__username__icontains=q))

    return Response(
        [
            {
                'id': item.id,
                'action': item.action,
                'actor_id': item.actor_id,
                'actor_username': item.actor.username if item.actor else '',
                'target_type': item.target_type,
                'target_id': item.target_id,
                'target_label': item.target_label,
                'detail': item.detail,
                'ip_address': item.ip_address,
                'created_at': item.created_at,
            }
            for item in queryset[:limit]
        ]
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_control_exam(request, exam_id):
    """管理员全局控制考试状态：pause/resume/end。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can control exams'}, status=403)

    exam = get_object_or_404(Exam, id=exam_id)
    action = str(request.data.get('action', '')).strip().lower()
    mapping = {
        'pause': 'paused',
        'resume': 'running',
        'end': 'ended',
    }
    if action not in mapping:
        return Response({'error': 'action must be pause/resume/end'}, status=400)

    exam.control_status = mapping[action]
    exam.save(update_fields=['control_status'])

    _log_operation(
        request,
        action='admin_control_exam',
        actor=request.user,
        target_type='exam',
        target_id=exam.id,
        target_label=exam.title,
        detail=f"control_status={exam.control_status}",
    )

    return Response({'exam_id': exam.id, 'title': exam.title, 'control_status': exam.control_status})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def admin_system_config(request):
    """管理员查看/更新系统基础运行配置。"""
    if not _require_admin(request.user):
        return Response({'error': 'only admin can update system config'}, status=403)

    config = SystemConfig.objects.first()
    if not config:
        config = SystemConfig.objects.create(updated_by=request.user)

    if request.method == 'PUT':
        auto_save_interval_seconds = request.data.get('auto_save_interval_seconds')
        max_exam_concurrency = request.data.get('max_exam_concurrency')

        if auto_save_interval_seconds is not None:
            try:
                auto_save_interval_seconds = int(auto_save_interval_seconds)
            except (TypeError, ValueError):
                return Response({'error': 'auto_save_interval_seconds must be an integer'}, status=400)
            if auto_save_interval_seconds < 5:
                return Response({'error': 'auto_save_interval_seconds must be >= 5'}, status=400)
            config.auto_save_interval_seconds = auto_save_interval_seconds

        if max_exam_concurrency is not None:
            try:
                max_exam_concurrency = int(max_exam_concurrency)
            except (TypeError, ValueError):
                return Response({'error': 'max_exam_concurrency must be an integer'}, status=400)
            if max_exam_concurrency < 1:
                return Response({'error': 'max_exam_concurrency must be >= 1'}, status=400)
            config.max_exam_concurrency = max_exam_concurrency

        config.updated_by = request.user
        config.save()

        _log_operation(
            request,
            action='admin_update_system_config',
            actor=request.user,
            target_type='system_config',
            target_id=config.id,
            target_label='SystemConfig',
            detail=(
                f"auto_save_interval_seconds={config.auto_save_interval_seconds} "
                f"max_exam_concurrency={config.max_exam_concurrency}"
            ),
        )

    return Response(
        {
            'id': config.id,
            'auto_save_interval_seconds': config.auto_save_interval_seconds,
            'max_exam_concurrency': config.max_exam_concurrency,
            'updated_by': config.updated_by.username if config.updated_by else '',
            'updated_at': config.updated_at,
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_submissions(request):
    """学生查看自己的提交与成绩接口。"""
    if _get_role(request.user) != 'student':
        return Response({'error': 'only student can view own submissions'}, status=403)

    data = []
    for item in (
        Submission.objects.filter(student=request.user)
        .select_related('exam')
        .all()
        .order_by('-submitted_at')
    ):
        data.append(
            {
                'submission_id': item.id,
                'exam_id': item.exam.id,
                'exam_title': item.exam.title,
                'course_name': item.exam.course.name if item.exam.course else '',
                'status': item.status,
                'is_result_published': item.is_result_published,
                'total_score': item.total_score if item.is_result_published else None,
                'max_score': item.max_score if item.is_result_published else None,
                'submitted_at': item.submitted_at,
            }
        )
    return Response(data)
