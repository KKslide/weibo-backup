import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/post/:id',
    name: 'PostDetail',
    component: () => import('../views/PostDetail.vue')
  },
  {
    path: '/timeline',
    name: 'Timeline',
    component: () => import('../views/Timeline.vue')
  },
  {
    path: '/images',
    name: 'Images',
    component: () => import('../views/Images.vue')
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('../views/Search.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
