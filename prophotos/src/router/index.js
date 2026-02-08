import { createRouter, createWebHistory } from 'vue-router';
import HomePage from '@/views/HomePage.vue';
import LoginPage from '@/views/LoginPage.vue';
import ImagePage from '@/views/ImagePage.vue';
import RecfacPage from '@/views/RecfacPage.vue';
import PersonnesPage from '@/views/PersonnesPage.vue';
import UsersPage from '@/views/UsersPage.vue';
import { USERS_API_URL } from '@/constants';

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
  {
    path: '/image',
    name: 'Image',
    component: ImagePage,
    meta: { requiresAuth: true },
  },
  {
    path: '/recfac',
    name: 'Recfac',
    component: RecfacPage,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/personnes',
    name: 'Personnes',
    component: PersonnesPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/utilisateurs',
    name: 'Utilisateurs',
    component: UsersPage,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation guard pour vérifier l'authentification
router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('token');

  // Si la route nécessite une authentification
  if (to.meta.requiresAuth) {
    if (!token) {
      // Pas de token, rediriger vers login
      return next({ name: 'Login', query: { redirect: to.fullPath } });
    }

    // Vérifier si le token est valide et récupérer le statut admin
    try {
      const response = await fetch(`${USERS_API_URL}/users/verify-token/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        // Token invalide, supprimer et rediriger
        localStorage.removeItem('token');
        localStorage.removeItem('isAdmin');
        return next({ name: 'Login', query: { redirect: to.fullPath } });
      }

      const data = await response.json();

      // Si la route nécessite admin et l'utilisateur n'est pas admin
      if (to.meta.requiresAdmin && !data.user?.admin) {
        return next({ name: 'Images' });
      }

    } catch (error) {
      // Erreur réseau, supprimer token et rediriger
      localStorage.removeItem('token');
      localStorage.removeItem('isAdmin');
      return next({ name: 'Login', query: { redirect: to.fullPath } });
    }
  }

  next();
});

export default router;
