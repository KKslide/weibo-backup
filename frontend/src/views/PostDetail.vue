<template>
  <div class="post-detail" v-loading="loading">
    <el-page-header @back="$router.back()" :title="'返回'">
      <template #content>
        <span class="page-title">微博详情</span>
      </template>
    </el-page-header>

    <div v-if="post" class="content-wrapper">
      <!-- 微博主体 -->
      <el-card class="post-card">
        <div class="post-header">
          <el-avatar :size="48" :src="user?.avatar_url" />
          <div class="user-info">
            <span class="username">{{ user?.screen_name || '未知用户' }}</span>
            <span class="post-time">{{ formatTime(post.created_at) }}</span>
          </div>
          <el-tag v-if="post.source" size="small" type="info">{{ post.source }}</el-tag>
        </div>

        <div class="post-text" v-html="post.text"></div>

        <!-- 图片 -->
        <div v-if="post.images?.length" class="post-images">
          <el-image
            v-for="img in post.images"
            :key="img.id"
            :src="getMediaUrl(img)"
            :preview-src-list="[img.url]"
            fit="cover"
            class="post-image"
          />
        </div>

        <!-- 视频 -->
        <div v-if="post.videos?.length" class="post-videos">
          <video
            v-for="video in post.videos"
            :key="video.id"
            :src="video.url"
            controls
            class="post-video"
          />
        </div>

        <div class="post-stats">
          <span><el-icon><Star /></el-icon> {{ post.attitudes_count }} 赞</span>
          <span><el-icon><ChatDotRound /></el-icon> {{ post.comments_count }} 评论</span>
          <span><el-icon><Share /></el-icon> {{ post.reposts_count }} 转发</span>
        </div>
      </el-card>

      <!-- 点赞用户 -->
      <el-card v-if="post.likes?.length" class="section-card">
        <template #header>点赞用户 ({{ post.likes.length }})</template>
        <div class="likes-list">
          <div v-for="like in post.likes" :key="like.user_uid" class="like-item">
            <el-avatar :size="32" :src="like.user_avatar" />
            <span>{{ like.user_name }}</span>
          </div>
        </div>
      </el-card>

      <!-- 评论列表 -->
      <el-card v-if="post.comments?.length" class="section-card">
        <template #header>评论 ({{ post.comments.length }})</template>
        <div class="comments-list">
          <div v-for="comment in post.comments" :key="comment.id" class="comment-item">
            <div class="comment-header">
              <el-avatar :size="36" :src="comment.user_avatar" />
              <div class="comment-user">
                <span class="comment-username">{{ comment.user_name }}</span>
                <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
              </div>
              <span class="comment-likes" v-if="comment.like_count">
                <el-icon><Star /></el-icon> {{ comment.like_count }}
              </span>
            </div>
            <div class="comment-text" v-html="comment.text"></div>

            <!-- 回复 -->
            <div v-if="comment.replies?.length" class="replies">
              <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
                <span class="reply-user">{{ reply.user_name }}</span>
                <span v-if="reply.reply_to_name" class="reply-to">
                  回复 <span class="reply-target">{{ reply.reply_to_name }}</span>
                </span>
                <span class="reply-text" v-html="reply.text"></span>
                <span class="reply-time">{{ formatTime(reply.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPost, getUser } from '../api'
import { formatTime, getMediaUrl } from '../utils'

const route = useRoute()
const post = ref(null)
const user = ref(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const [postRes, userRes] = await Promise.all([
      getPost(route.params.id),
      getUser()
    ])
    post.value = postRes.data
    user.value = userRes.data
  } catch (error) {
    console.error('加载微博详情失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.post-detail {
  max-width: 800px;
  margin: 0 auto;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
}

.content-wrapper {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.post-card :deep(.el-card__body) {
  padding: 20px;
}

.post-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.user-info {
  flex: 1;
}

.username {
  display: block;
  font-weight: 500;
  color: #333;
}

.post-time {
  font-size: 12px;
  color: #999;
}

.post-text {
  line-height: 1.8;
  color: #333;
  margin-bottom: 16px;
}

.post-text :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.post-text :deep(.url-icon) {
  display: none;
}

.post-images {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.post-image {
  width: 100%;
  height: 200px;
  border-radius: 8px;
}

.post-video {
  width: 100%;
  max-height: 400px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.post-stats {
  display: flex;
  gap: 24px;
  color: #666;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.post-stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.section-card :deep(.el-card__header) {
  font-weight: 500;
}

.likes-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.like-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comment-item {
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.comment-user {
  flex: 1;
}

.comment-username {
  display: block;
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

.comment-time {
  font-size: 12px;
  color: #999;
}

.comment-likes {
  color: #999;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.comment-text {
  color: #333;
  line-height: 1.6;
  margin-left: 46px;
}

.replies {
  margin-left: 46px;
  margin-top: 12px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
}

.reply-item {
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.reply-item:last-child {
  margin-bottom: 0;
}

.reply-user {
  color: #409eff;
  font-weight: 500;
}

.reply-to {
  color: #999;
}

.reply-target {
  color: #409eff;
}

.reply-text {
  color: #333;
}

.reply-time {
  color: #999;
  font-size: 12px;
  margin-left: 8px;
}
</style>
