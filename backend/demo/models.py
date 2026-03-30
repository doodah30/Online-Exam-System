from django.db import models
from django.contrib.auth.models import User


# 数据库存储说明：
# 1) 用户基础信息在 Django 内置 auth_user 表（由 User 模型管理）
# 2) 角色信息在 UserProfile 表
# 3) 题库、试卷、答卷、课程等业务数据都在本文件定义的表


class UserProfile(models.Model):
	"""扩展用户信息，仅负责保存角色（admin/teacher/student）。"""

	ROLE_CHOICES = (
		('admin', 'Admin'),
		('student', 'Student'),
		('teacher', 'Teacher'),
	)

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)

	def __str__(self):
		return f"{self.user.username} ({self.role})"


class Exam(models.Model):
	"""试卷主表：记录考试基础信息与所属课程。"""

	RESULT_POLICY_CHOICES = (
		('teacher_release', 'Teacher Release'),
		('auto_release', 'Auto Release'),
	)

	CONTROL_STATUS_CHOICES = (
		('running', 'Running'),
		('paused', 'Paused'),
		('ended', 'Ended'),
	)

	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	duration_minutes = models.PositiveIntegerField(default=60)
	is_published = models.BooleanField(default=True)
	result_policy = models.CharField(max_length=20, choices=RESULT_POLICY_CHOICES, default='teacher_release')
	control_status = models.CharField(max_length=20, choices=CONTROL_STATUS_CHOICES, default='running')
	course = models.ForeignKey('Course', on_delete=models.SET_NULL, related_name='exams', null=True, blank=True)
	created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_exams')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.title


class Question(models.Model):
	"""试卷题目表：支持单选题和主观题。"""

	QUESTION_TYPE_CHOICES = (
		('single', 'Single Choice'),
		('subjective', 'Subjective'),
	)

	exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
	question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='single')
	text = models.TextField()
	option_a = models.CharField(max_length=255, blank=True)
	option_b = models.CharField(max_length=255, blank=True)
	option_c = models.CharField(max_length=255, blank=True)
	option_d = models.CharField(max_length=255, blank=True)
	correct_option = models.IntegerField(null=True, blank=True)
	reference_answer = models.TextField(blank=True)
	keyword_answers = models.CharField(max_length=500, blank=True)
	# bank_item 表示该题是否来源于题库题
	bank_item = models.ForeignKey('QuestionBankItem', on_delete=models.SET_NULL, related_name='used_in_questions', null=True, blank=True)
	score = models.PositiveIntegerField(default=10)

	def __str__(self):
		return f"Q{self.id} - {self.exam.title}"


class Submission(models.Model):
	"""学生交卷记录：每个学生对同一张试卷只能提交一次。"""

	STATUS_CHOICES = (
		('submitted', 'Submitted'),
		('graded', 'Graded'),
	)

	exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='submissions')
	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
	total_score = models.PositiveIntegerField(default=0)
	max_score = models.PositiveIntegerField(default=0)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
	is_result_published = models.BooleanField(default=False)
	published_at = models.DateTimeField(null=True, blank=True)
	submitted_at = models.DateTimeField(auto_now_add=True)
	graded_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('exam', 'student')

	def __str__(self):
		return f"{self.student.username} - {self.exam.title}"


class Answer(models.Model):
	"""单题作答记录：属于某次 Submission。"""

	submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
	question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
	selected_option = models.IntegerField(null=True, blank=True)
	subjective_answer = models.TextField(blank=True)
	is_manual_graded = models.BooleanField(default=False)
	is_correct = models.BooleanField(default=False)
	score_awarded = models.PositiveIntegerField(default=0)
	auto_feedback = models.CharField(max_length=255, blank=True)

	def __str__(self):
		return f"Answer {self.id} for submission {self.submission_id}"


class Course(models.Model):
	"""课程表：老师创建课程，用于按课程分配试卷。"""

	name = models.CharField(max_length=200)
	subject_tag = models.CharField(max_length=50, default='common')
	description = models.TextField(blank=True)
	teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name


class CourseEnrollment(models.Model):
	"""选课关系表：学生加入课程后才能看到该课程下的试卷。"""

	course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
	student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_enrollments')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('course', 'student')

	def __str__(self):
		return f"{self.course.name} - {self.student.username}"


class QuestionBankItem(models.Model):
	"""题库表：老师维护可复用题目，出卷时可直接引用。"""

	teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_bank_items')
	subject_tag = models.CharField(max_length=50, default='common')
	tags = models.CharField(max_length=200, blank=True)
	difficulty = models.PositiveSmallIntegerField(default=3)
	question_type = models.CharField(max_length=20, choices=Question.QUESTION_TYPE_CHOICES, default='single')
	text = models.TextField()
	option_a = models.CharField(max_length=255, blank=True)
	option_b = models.CharField(max_length=255, blank=True)
	option_c = models.CharField(max_length=255, blank=True)
	option_d = models.CharField(max_length=255, blank=True)
	correct_option = models.IntegerField(null=True, blank=True)
	reference_answer = models.TextField(blank=True)
	keyword_answers = models.CharField(max_length=500, blank=True)
	score = models.PositiveIntegerField(default=10)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"BankItem {self.id} - {self.teacher.username}"


class OperationLog(models.Model):
	"""系统关键操作日志，用于审计追踪。"""

	action = models.CharField(max_length=100)
	actor = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='operation_logs', null=True, blank=True)
	target_type = models.CharField(max_length=50, blank=True)
	target_id = models.IntegerField(null=True, blank=True)
	target_label = models.CharField(max_length=200, blank=True)
	detail = models.TextField(blank=True)
	ip_address = models.CharField(max_length=64, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		actor_name = self.actor.username if self.actor else 'anonymous'
		return f"{self.action} by {actor_name}"


class SystemConfig(models.Model):
	"""系统运行配置（单例）。"""

	auto_save_interval_seconds = models.PositiveIntegerField(default=30)
	max_exam_concurrency = models.PositiveIntegerField(default=200)
	updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='updated_system_configs', null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return "SystemConfig"


class EmailVerificationCode(models.Model):
	"""邮箱验证码：用于找回密码和绑定邮箱。"""

	PURPOSE_CHOICES = (
		('reset_password', 'Reset Password'),
		('bind_email', 'Bind Email'),
	)

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_codes', null=True, blank=True)
	username_snapshot = models.CharField(max_length=150, blank=True)
	email = models.EmailField()
	purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
	code = models.CharField(max_length=6)
	expires_at = models.DateTimeField()
	used_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['email', 'purpose', '-created_at']),
			models.Index(fields=['username_snapshot', 'purpose', '-created_at']),
		]

	def __str__(self):
		return f"{self.email} ({self.purpose})"
