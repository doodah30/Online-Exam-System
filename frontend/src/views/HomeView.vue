<template>
  <section class="stack-lg">
    <article class="panel hero-landing stack">
      <p class="eyebrow">Online Exam Platform</p>
      <h2>智能在线考试平台</h2>
      <p>
        覆盖课程教学全流程：老师管理课程与题库、发布试卷并阅卷，学生在线答题并查看成绩，管理员统一治理系统。
      </p>
      <div class="grid two-col feature-grid">
        <div class="card">老师端：课程管理、题库管理、组卷与阅卷</div>
        <div class="card">学生端：在线考试、自动交卷、成绩查看</div>
        <div class="card">管理员端：用户管理、日志审计、考试总控</div>
        <div class="card">邮箱能力：验证码找回密码、账号绑定邮箱</div>
      </div>
      <p class="tiny muted">请点击右上角“登录 / 注册”进入账号页。</p>
    </article>
  </section>
</template>

<style scoped>
.hero-landing h2 {
  font-size: clamp(1.8rem, 4vw, 2.7rem);
  line-height: 1.15;
  margin: 0.3rem 0 1rem;
}

.hero-landing p {
  color: var(--muted);
}

.eyebrow {
  font-size: 0.8rem;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--brand-deep);
  font-weight: 700;
}

.feature-grid {
  margin-top: 0.5rem;
}
</style>
