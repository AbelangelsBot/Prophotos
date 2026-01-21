import { createRouter, createWebHistory } from 'vue-router';
import HomePage from '@/views/HomePage.vue';
import LoginPage from '@/views/LoginPage.vue';
import ImagePage from '@/views/ImagePage.vue';
import RecfacPage from '@/views/RecfacPage.vue';
import PersonnesPage from '@/views/PersonnesPage.vue';

const routes = [
  { path: '/', redirect: '/images' },
  {
    path: '/images/:pathMatch(.*)*',
    name: 'Images',
    component: HomePage,
  },
  {
    path: '/home/:pathMatch(.*)*',
    redirect: (to) => {
      const suffix = to.params.pathMatch ? `/${to.params.pathMatch}` : '';
      return `/images${suffix}`;
    },
  },
  { path: '/login', name: 'Login', component: LoginPage },
  { path: '/image', name: 'Image', component: ImagePage },
  { path: '/recfac', name: 'Recfac', component: RecfacPage },
  { path: '/personnes', name: 'Personnes', component: PersonnesPage },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
