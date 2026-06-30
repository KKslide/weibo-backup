<template>
  <el-config-provider :locale="zhCn">
    <div id="app">
      <el-container>
        <el-header>
          <div class="header-content">
            <el-menu mode="horizontal" :router="true" :default-active="$route.path" :ellipsis="false">
              <el-menu-item index="/">首页</el-menu-item>
              <el-menu-item index="/timeline" @click="$router.push({ path: '/timeline' })">时间线</el-menu-item>
              <el-menu-item index="/images">图片</el-menu-item>
              <el-menu-item index="/search">搜索</el-menu-item>
            </el-menu>
          </div>
        </el-header>
        <el-main>
          <router-view v-slot="{ Component }">
            <keep-alive include="Timeline">
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
}

#app {
  min-height: 100vh;
}

.el-header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60px;
}

.el-menu {
  border-bottom: none !important;
}

.el-menu--horizontal > .el-menu-item {
  padding: 0 20px;
}

.el-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  min-height: calc(100vh - 60px);
}

/* 微博表情图片全局样式 */
.post-text img,
.comment-text img,
.reply-text img {
  width: 20px !important;
  height: 20px !important;
  max-width: 20px !important;
  max-height: 20px !important;
  vertical-align: middle;
  margin: 0 2px;
}

.post-text .emoji,
.comment-text .emoji {
  width: 20px !important;
  height: 20px !important;
}

.post-text img[src*="face"],
.post-text img[src*="emoji"],
.comment-text img[src*="face"],
.comment-text img[src*="emoji"] {
  width: 20px !important;
  height: 20px !important;
  max-width: 20px !important;
  max-height: 20px !important;
}

/* 回复中的表情 */
.post-detail .reply-text img {
  width: 20px !important;
  height: 20px !important;
  max-width: 20px !important;
  max-height: 20px !important;
  vertical-align: middle;
  margin: 0 2px;
}
</style>
