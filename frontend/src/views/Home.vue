<template>
  <div class="home">
    <!-- 用户信息 -->
    <el-card v-if="user" class="user-card">
      <div class="user-info">
        <el-avatar :size="72" :src="user.avatar_url" />
        <div class="user-details">
          <h2>{{ user.screen_name }}</h2>
          <p class="user-desc">{{ user.description || '这个人很懒，什么都没写' }}</p>
          <div class="user-stats">
            <div class="stat-item">
              <div class="stat-value">{{ user.followers_count }}</div>
              <div class="stat-label">粉丝</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ user.follow_count }}</div>
              <div class="stat-label">关注</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ user.statuses_count }}</div>
              <div class="stat-label">微博</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ user.total_engagement }}</div>
              <div class="stat-label">转评赞</div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 那年今日 -->
    <el-card class="section-card">
      <template #header>
        <div class="section-header">
          <span>那年今日{{ onThisDayDate ? ` · ${onThisDayDate}` : '' }}</span>
        </div>
      </template>

      <div v-loading="loading" class="posts-list">
        <div v-for="post in posts" :key="post.id" class="post-item" @click="$router.push(`/post/${post.id}`)">
          <div class="post-content">
            <p class="post-text" v-html="post.text"></p>
            <div class="post-meta">
              <span class="post-time">{{ formatTime(post.created_at) }}</span>
              <div class="post-stats">
                <span><el-icon><Star /></el-icon> {{ post.attitudes_count }}</span>
                <span><el-icon><ChatDotRound /></el-icon> {{ post.comments_count }}</span>
                <span><el-icon><Share /></el-icon> {{ post.reposts_count }}</span>
              </div>
            </div>
          </div>
          <el-tag v-if="post.has_media" size="small" type="info">含媒体</el-tag>
        </div>
        <el-empty v-if="!posts.length && !loading" description="历史上的今天没有微博" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getUser, getOnThisDay } from '../api'
import { formatTime } from '../utils'

const user = ref(null)
const posts = ref([])
const onThisDayDate = ref('')
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const [userRes, postsRes] = await Promise.all([
      getUser(),
      getOnThisDay()
    ])
    user.value = userRes.data
    posts.value = postsRes.data.posts || []
    onThisDayDate.value = postsRes.data.date || ''
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.user-card :deep(.el-card__body) {
  padding: 24px;
}

.user-info {
  display: flex;
  gap: 24px;
  align-items: center;
}

.user-details h2 {
  margin-bottom: 8px;
  color: #333;
  font-size: 20px;
}

.user-desc {
  color: #666;
  margin-bottom: 16px;
  font-size: 14px;
}

.user-stats {
  display: flex;
  gap: 32px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.section-card {
  margin-top: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.post-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.post-item:hover {
  background: #f0f0f0;
}

.post-content {
  flex: 1;
}

.post-text {
  color: #333;
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.post-time {
  color: #999;
  font-size: 12px;
}

.post-stats {
  display: flex;
  gap: 16px;
  color: #666;
  font-size: 13px;
}

.post-stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
