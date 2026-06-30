<template>
  <div class="timeline-page">
    <div class="page-header">
      <h2>时间线</h2>
      <el-button v-if="selectedYear" text @click="goBack">
        <el-icon><Back /></el-icon> 返回
      </el-button>
    </div>

    <div v-loading="loading && page === 1">
      <!-- 年份 grid -->
      <div v-if="!selectedYear" class="years-grid">
        <div v-for="year in years" :key="year" class="year-card" @click="selectYear(year)">
          <div class="year-number">{{ year }}</div>
        </div>
      </div>

      <!-- 微博列表 -->
      <div v-else class="posts-list">
        <div
          v-for="post in posts"
          :key="post.id"
          class="post-card"
          :class="{ highlighted: post.id === highlightedPostId }"
          @click="goToPost(post.id)"
        >
          <div class="post-time">{{ formatTime(post.created_at) }}</div>
          <p class="post-text" v-html="post.text"></p>
          <div class="post-meta">
            <span class="post-stats">
              <span><el-icon><Star /></el-icon> {{ post.attitudes_count || 0 }}</span>
              <span><el-icon><ChatDotRound /></el-icon> {{ post.comments_count || 0 }}</span>
              <span><el-icon><Share /></el-icon> {{ post.reposts_count || 0 }}</span>
            </span>
            <el-tag v-if="post.has_media" size="small" type="info">含媒体</el-tag>
          </div>
        </div>

        <el-empty v-if="!posts.length && !loading" description="暂无数据" />

        <div v-if="hasMore" class="load-more">
          <el-button :loading="loading" @click="loadMore">加载更多</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default { name: 'Timeline' }
</script>

<script setup>
import { ref, onMounted, onActivated, onDeactivated, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getTimeline } from '../api'
import { formatTime } from '../utils'

const router = useRouter()
const route = useRoute()

const years = ref([])
const posts = ref([])
const selectedYear = ref('')
const loading = ref(false)
const page = ref(1)
const hasMore = ref(false)
const pageSize = 20
const savedScrollTop = ref(0)
const highlightedPostId = ref(null)

const loadTimeline = async (reset = true) => {
  if (!selectedYear.value) {
    posts.value = []
    return
  }

  if (reset) {
    page.value = 1
    posts.value = []
  }

  loading.value = true
  try {
    const res = await getTimeline({ year: selectedYear.value, page: page.value, size: pageSize })
    const data = res.data
    if (reset) {
      posts.value = data.posts || []
    } else {
      posts.value.push(...(data.posts || []))
    }
    hasMore.value = data.has_more || false
  } catch (error) {
    console.error('加载时间线失败:', error)
  } finally {
    loading.value = false
  }
}

const loadMore = () => {
  page.value++
  loadTimeline(false)
}

const selectYear = (year) => {
  selectedYear.value = year
  router.push({ query: { year } })
  loadTimeline(true)
}

const goBack = () => {
  selectedYear.value = ''
  posts.value = []
  router.push({ query: {} })
}

const goToPost = (id) => {
  highlightedPostId.value = id
  router.push(`/post/${id}`)
}

// 监听路由变化：当导航到 /timeline 且没有 year 参数时，重置为年份列表
watch(() => route.fullPath, () => {
  if (route.path === '/timeline' && !route.query.year) {
    selectedYear.value = ''
    posts.value = []
  }
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await getTimeline()
    years.value = (res.data.years || []).sort((a, b) => Number(b) - Number(a))

    // 直接访问 /timeline?year=2025 的情况
    if (route.query.year) {
      selectedYear.value = route.query.year
      await loadTimeline(true)
    }
  } catch (error) {
    console.error('加载年份失败:', error)
  } finally {
    loading.value = false
  }
})

// keep-alive: 组件激活时恢复滚动位置，高亮点击的博文
onActivated(() => {
  nextTick(() => {
    const mainEl = document.querySelector('.el-main')
    if (mainEl) {
      mainEl.scrollTop = savedScrollTop.value
    }

    // 2秒后清除高亮
    if (highlightedPostId.value) {
      setTimeout(() => {
        highlightedPostId.value = null
      }, 2000)
    }
  })
})

// keep-alive: 组件失活时保存滚动位置
onDeactivated(() => {
  const mainEl = document.querySelector('.el-main')
  if (mainEl) {
    savedScrollTop.value = mainEl.scrollTop
  }
})
</script>

<style scoped>
.timeline-page {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.years-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.year-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  width: 100px;
  padding: 20px 0;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: opacity 0.2s;
}

.year-card:hover {
  opacity: 0.85;
}

.year-number {
  font-size: 32px;
  font-weight: bold;
}

.year-label {
  font-size: 14px;
  opacity: 0.8;
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.load-more {
  text-align: center;
  padding: 16px 0;
}

.post-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.3s;
}

.post-card:hover {
  border-color: #c0c4cc;
}

.post-card.highlighted {
  background-color: #fef3cd;
  border-color: #ffc107;
}

.post-time {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.post-text {
  color: #333;
  line-height: 1.6;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.post-stats {
  display: flex;
  gap: 12px;
  color: #999;
  font-size: 13px;
}

.post-stats span {
  display: flex;
  align-items: center;
  gap: 3px;
}
</style>
