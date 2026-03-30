from django.urls import path

from .views import (
    admin_change_own_password,
    admin_control_exam,
    admin_operation_logs,
    admin_reset_user_password,
    admin_system_config,
    admin_user_detail,
    admin_users,
    auth_login,
    auth_me,
    auth_bind_email_with_code,
    auth_reset_password_with_code,
    auth_register,
    auth_send_bind_email_code,
    auth_send_password_reset_code,
    course_stats,
    course_students,
    courses,
    exam_detail,
    exam_grading_overview,
    exam_submissions,
    exams,
    grade_submission,
    hello_world,
    my_submissions,
    question_bank,
    question_bank_detail,
    question_bank_meta,
    release_exam_results,
    students,
    submit_exam,
)

urlpatterns = [
    # 健康检查
    path('hello/', hello_world),

    # 认证
    path('auth/register/', auth_register),
    path('auth/login/', auth_login),
    path('auth/me/', auth_me),
    path('auth/password-reset/send-code/', auth_send_password_reset_code),
    path('auth/password-reset/confirm/', auth_reset_password_with_code),
    path('auth/email/send-bind-code/', auth_send_bind_email_code),
    path('auth/email/bind/', auth_bind_email_with_code),

    # 学生查询与课程
    path('students/', students),
    path('courses/', courses),
    path('courses/<int:course_id>/students/', course_students),
    path('courses/<int:course_id>/stats/', course_stats),

    # 题库
    path('question-bank/meta/', question_bank_meta),
    path('question-bank/', question_bank),
    path('question-bank/<int:item_id>/', question_bank_detail),

    # 试卷与作答
    path('exams/', exams),
    path('exams/<int:exam_id>/', exam_detail),
    path('exams/<int:exam_id>/submit/', submit_exam),

    # 阅卷与发布
    path('exams/<int:exam_id>/grading/', exam_grading_overview),
    path('exams/<int:exam_id>/release-results/', release_exam_results),
    path('exams/<int:exam_id>/submissions/', exam_submissions),
    path('submissions/<int:submission_id>/grade/', grade_submission),

    # 学生查看自己的提交
    path('submissions/mine/', my_submissions),

    # 管理员能力
    path('admin/users/', admin_users),
    path('admin/users/<int:user_id>/', admin_user_detail),
    path('admin/users/<int:user_id>/reset-password/', admin_reset_user_password),
    path('admin/me/change-password/', admin_change_own_password),
    path('admin/logs/', admin_operation_logs),
    path('admin/exams/<int:exam_id>/control/', admin_control_exam),
    path('admin/system-config/', admin_system_config),
]
