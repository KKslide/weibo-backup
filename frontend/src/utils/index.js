/**
 * 格式化微博时间
 * @param {string} time - 微博时间字符串
 * @returns {string} 格式化后的时间
 */
export const formatTime = (time) => {
  if (!time) return ''
  const d = new Date(time)
  if (isNaN(d.getTime())) return time
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  const day = d.getDate()
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${year}年${month}月${day}日 ${hour}:${minute}`
}

/**
 * 获取媒体资源 URL（本地路径优先）
 * @param {object} item - 媒体对象，包含 local_path 和 url 字段
 * @returns {string} 媒体资源 URL
 */
export const getMediaUrl = (item) => {
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  if (item.local_path) {
    return `${apiBase}/media/${item.local_path}`
  }
  return item.url
}
