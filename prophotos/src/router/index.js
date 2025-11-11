import { createRouter, createWebHistory } from 'vue-router';
import HomePage from '@/views/HomePage.vue';
import LoginPage from '@/views/LoginPage.vue';
import ImagePage from '@/views/ImagePage.vue';

const routes = [
  { path: '/', name: 'Home', component: HomePage },
  { path: '/login', name: 'Login', component: LoginPage },
  { path: '/image', name: 'Image', component: ImagePage },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
