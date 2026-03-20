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
    Question,
    QuestionBankItem,
    Submission,
    UserProfile,
)


# 这个文件是后端业务入口：
# - 认证（注册、登录、当前用户）
# - 课程与选课
# - 题库维护
# - 试卷创建、作答、阅卷、统计


@api_view(['GET'])
def hello_world(request):
    return Response({'message': 'Hello from Django!'})


def _get_role(user):
    # 角色信息来自 UserProfile 表，而不是 auth_user 表。
    if not hasattr(user, 'profile'):
        return None
    return user.profile.role


def _require_teacher(user):
    role = _get_role(user)
    return role == 'teacher'


def _parse_keywords(raw_text):
    return [item.strip().lower() for item in str(raw_text).split(',') if item.strip()]


def _split_tags(raw_tags):
    return [item.strip() for item in str(raw_tags).split(',') if item.strip()]


def _grade_subjective(answer_text, keywords, full_score):
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
    has_subjective = exam.questions.filter(question_type='subjective').exists()
    payload = {
        'id': exam.id,
        'title': exam.title,
        'description': exam.description,
        'duration_minutes': exam.duration_minutes,
        'is_published': exam.is_published,
        'result_policy': exam.result_policy,
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
    # 注册时会写入两张表：
    # 1) auth_user（用户名、密码哈希）
    # 2) demo_userprofile（角色）
    # 同时生成 token（authtoken_token 表），供前端后续携带认证。
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    role = request.data.get('role', '').strip()

    if role not in ('student', 'teacher'):
        return Response({'error': 'role must be student or teacher'}, status=400)
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
    return Response(
        {
            'token': token.key,
            'user': {'id': user.id, 'username': user.username, 'role': user.profile.role},
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    role = _get_role(request.user)
    if not role:
        return Response({'error': 'profile missing'}, status=400)
    return Response({'id': request.user.id, 'username': request.user.username, 'role': role})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def students(request):
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
    role = _get_role(request.user)
    if role not in ('student', 'teacher'):
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

        return Response(_exam_to_dict(exam, include_questions=True, include_answer=True), status=201)

    if role == 'teacher':
        queryset = Exam.objects.filter(created_by=request.user).order_by('-created_at')
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
    # 提交试卷后会写入：
    # 1) Submission（一次交卷记录）
    # 2) Answer（每一题的作答与得分）
    # 客观题按正确选项判分，主观题按关键词自动评分。
    if _get_role(request.user) != 'student':
        return Response({'error': 'only student can submit'}, status=403)

    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

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

    return Response(payload, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exam_grading_overview(request, exam_id):
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_submissions(request):
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
