<template>
  <section class="stack-lg">
    <article class="panel">
      <h2>老师功能中心</h2>
      <p class="muted">请选择要进入的模块：题库管理、课程管理、试卷管理。</p>
    </article>

    <article class="grid two-col">
      <router-link class="panel card-link" to="/question-bank">
        <h3>题库管理</h3>
        <p>出题、搜索筛选、标签管理、难度维护、共享题库浏览。</p>
      </router-link>

      <router-link class="panel card-link" to="/course-management">
        <h3>课程管理</h3>
        <p>创建课程、配置课程标签、添加或移除学生、查看课程统计。</p>
      </router-link>

      <router-link class="panel card-link" to="/exam-management">
        <h3>试卷管理</h3>
        <p>从题库选题出卷、编辑试题内容、发布试卷与查看阅卷记录。</p>
      </router-link>
    </article>
  </section>
</template>

<style scoped>
.card-link {
  text-decoration: none;
  color: inherit;
  transition: transform 0.2s ease;
}

.card-link:hover {
  transform: translateY(-2px);
}
</style>
