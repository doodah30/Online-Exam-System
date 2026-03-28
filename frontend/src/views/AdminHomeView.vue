<template>
  <section class="stack-lg">
    <article class="panel">
      <h2>管理员控制台</h2>
      <p class="muted">统一维护用户体系、系统配置、操作审计与考试全局状态。</p>
    </article>

    <article class="grid two-col">
      <router-link class="panel card-link" to="/admin/users">
        <h3>用户管理</h3>
        <p>新增、编辑、删除、禁用用户，重置密码并设置角色。</p>
      </router-link>

      <router-link class="panel card-link" to="/admin/logs">
        <h3>操作日志</h3>
        <p>查看登录、考试发布、答卷提交等关键审计记录。</p>
      </router-link>

      <router-link class="panel card-link" to="/admin/exams">
        <h3>考试全局管控</h3>
        <p>快速暂停、恢复或强制结束指定考试。</p>
      </router-link>

      <router-link class="panel card-link" to="/admin/system-config">
        <h3>系统配置</h3>
        <p>配置自动保存间隔、考试并发上限等全局参数。</p>
      </router-link>

      <router-link class="panel card-link" to="/admin/change-password">
        <h3>修改我的密码</h3>
        <p>仅修改当前管理员账号密码，不影响其他账户管理规则。</p>
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
