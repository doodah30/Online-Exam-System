<template>
  <section class="grid two-col">
    <article class="panel hero-landing">
      <p class="eyebrow">Online Exam System</p>
      <h2>从出卷到阅卷，一站式教学评估</h2>
      <p>
        面向课程教学的在线考试应用：老师快速创建试卷，学生在线答题，系统自动判分并沉淀成绩记录。
      </p>
      <div class="row-wrap">
        <router-link class="primary" to="/auth">立即开始</router-link>
        <router-link class="ghost" to="/dashboard">进入控制台</router-link>
      </div>
    </article>

    <article class="panel stack">
      <h3>当前可用功能</h3>
      <div class="card">老师 / 学生双身份注册登录</div>
      <div class="card">老师创建单选题试卷并发布</div>
      <div class="card">学生在线作答并自动评分</div>
      <div class="card">老师查看考试提交与分数</div>
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

a.primary,
a.ghost {
  text-decoration: none;
}
</style>
