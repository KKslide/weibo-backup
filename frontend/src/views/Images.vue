<template>
  <div class="images-page">
    <el-card>
      <template #header>
        <div class="header">
          <span>图片库 ({{ total }})</span>
          <el-select v-model="sortOrder" style="width: 120px" @change="onSortChange">
            <el-option label="最新在前" value="desc" />
            <el-option label="最早在前" value="asc" />
          </el-select>
        </div>
      </template>

      <div v-loading="loading">
        <div class="image-grid">
          <div v-for="image in images" :key="image.id" class="image-item" @click="openImage(image)">
            <el-image
              :src="getMediaUrl(image)"
              fit="cover"
              class="image-thumb"
              lazy
            >
              <template #placeholder>
                <div class="image-loading">
                  <el-icon class="is-loading"><Loading /></el-icon>
                </div>
              </template>
            </el-image>
            <div class="image-info">
              <p class="image-date">{{ formatTime(image.created_at) }}</p>
            </div>
          </div>
        </div>

        <el-empty v-if="!images.length && !loading" description="暂无图片" />

        <!-- 分页 -->
        <div class="pagination" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="loadImages"
          />
        </div>
      </div>
    </el-card>

    <!-- 图片预览 -->
    <el-dialog v-model="previewVisible" title="图片详情" width="80%">
      <div class="preview-content" v-if="previewImage">
        <el-image :src="previewImage.url" fit="contain" class="preview-image" />
        <div class="preview-info">
          <p>发布时间: {{ formatTime(previewImage.created_at) }}</p>
          <p>微博内容: {{ previewImage.text_plain }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getImages } from '../api'
import { formatTime, getMediaUrl } from '../utils'

const images = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50
const loading = ref(false)
const previewVisible = ref(false)
const previewImage = ref(null)
const sortOrder = ref('desc')

const loadImages = async () => {
  loading.value = true
  try {
    const res = await getImages({
      page: currentPage.value,
      size: pageSize,
      sort_order: sortOrder.value
    })
    images.value = res.data.images || []
    total.value = res.data.total || 0
  } catch (error) {
    console.error('加载图片失败:', error)
  } finally {
    loading.value = false
  }
}

const onSortChange = () => {
  currentPage.value = 1
  loadImages()
}

const openImage = (image) => {
  previewImage.value = image
  previewVisible.value = true
}

onMounted(() => {
  loadImages()
})
</script>

<style scoped>
.images-page {
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.image-item {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
  transition: transform 0.2s, box-shadow 0.2s;
}

.image-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.image-thumb {
  width: 100%;
  aspect-ratio: 1;
}

.image-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
  color: #999;
}

.image-info {
  padding: 8px 12px;
}

.image-date {
  font-size: 12px;
  color: #999;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.preview-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.preview-image {
  max-height: 60vh;
}

.preview-info {
  color: #666;
  font-size: 14px;
}

.preview-info p {
  margin-bottom: 8px;
}
</style>
