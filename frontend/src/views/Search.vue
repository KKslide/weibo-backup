<template>
  <div class="search-page">
    <el-card>
      <template #header>
        <div class="search-header">
          <el-input
            v-model="keyword"
            placeholder="搜索微博内容..."
            clearable
            size="large"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #append>
              <el-button @click="handleSearch">搜索</el-button>
            </template>
          </el-input>
        </div>
      </template>

      <div v-loading="loading">
        <!-- 搜索结果 -->
        <div v-if="searched" class="search-results">
          <div class="result-header">
            <span>找到 {{ total }} 条相关微博</span>
          </div>

          <div class="result-list">
            <div
              v-for="post in posts"
              :key="post.id"
              class="result-item"
              @click="$router.push(`/post/${post.id}`)"
            >
              <div class="result-content">
                <p class="result-text" v-html="highlightText(post.text_plain)"></p>
                <div class="result-meta">
                  <span class="result-time">{{ formatTime(post.created_at) }}</span>
                  <div class="result-stats">
                    <span><el-icon><Star /></el-icon> {{ post.attitudes_count }}</span>
                    <span><el-icon><ChatDotRound /></el-icon> {{ post.comments_count }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <el-empty v-if="!posts.length && !loading" description="没有找到相关内容" />

          <!-- 分页 -->
          <div class="pagination" v-if="total > pageSize">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="total"
              layout="prev, pager, next"
              @current-change="loadResults"
            />
          </div>
        </div>

        <!-- 热门搜索建议 -->
        <div v-else class="search-suggestions">
          <h3>搜索建议</h3>
          <div class="suggestion-tags">
            <el-tag
              v-for="tag in suggestions"
              :key="tag"
              class="suggestion-tag"
              @click="searchSuggestion(tag)"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchPosts } from '../api'
import { formatTime } from '../utils'

const keyword = ref('')
const posts = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)
const searched = ref(false)

const suggestions = ['旅行', '美食', '电影', '音乐', '工作', '生活', '读书', '运动']

const handleSearch = () => {
  if (!keyword.value.trim()) return
  currentPage.value = 1
  searched.value = true
  loadResults()
}

const searchSuggestion = (tag) => {
  keyword.value = tag
  handleSearch()
}

const loadResults = async () => {
  loading.value = true
  try {
    const res = await searchPosts({
      q: keyword.value,
      page: currentPage.value,
      size: pageSize
    })
    posts.value = res.data.posts || []
    total.value = res.data.total || 0
  } catch (error) {
    console.error('搜索失败:', error)
  } finally {
    loading.value = false
  }
}

const highlightText = (text) => {
  if (!keyword.value || !text) return text
  const regex = new RegExp(`(${keyword.value})`, 'gi')
  return text.replace(regex, '<span class="highlight">$1</span>')
}
</script>

<style scoped>
.search-page {
  max-width: 800px;
  margin: 0 auto;
}

.search-header {
  padding: 10px 0;
}

.result-header {
  margin-bottom: 20px;
  color: #666;
  font-size: 14px;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.result-item:hover {
  background: #f0f0f0;
  transform: translateX(4px);
}

.result-text {
  color: #333;
  line-height: 1.6;
  margin-bottom: 12px;
}

.result-text :deep(.highlight) {
  color: #ff6b6b;
  font-weight: 500;
  background: rgba(255, 107, 107, 0.1);
  padding: 0 2px;
  border-radius: 2px;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-time {
  color: #999;
  font-size: 12px;
}

.result-stats {
  display: flex;
  gap: 16px;
  color: #666;
  font-size: 13px;
}

.result-stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.search-suggestions {
  text-align: center;
  padding: 40px 0;
}

.search-suggestions h3 {
  color: #999;
  margin-bottom: 20px;
  font-weight: normal;
}

.suggestion-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

.suggestion-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-tag:hover {
  transform: scale(1.1);
}
</style>
