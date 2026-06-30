import axios from 'axios'

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${apiBase}/api`,
  timeout: 10000
})

// 获取用户信息
export const getUser = () => api.get('/user')

// 获取微博列表
export const getPosts = (params) => api.get('/posts', { params })

// 获取微博详情
export const getPost = (id) => api.get(`/posts/${id}`)

// 搜索微博
export const searchPosts = (params) => api.get('/search', { params })

// 获取时间线
export const getTimeline = (params) => api.get('/timeline', { params })

// 获取图片列表
export const getImages = (params) => api.get('/images', { params })

// 获取历史上的今天
export const getOnThisDay = () => api.get('/on_this_day')

export default api
