import store from '../store';

export default function beforeEach(to, from, next) {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const isAuthenticated = store.getters['user/isAuthenticated'];
  if (requiresAuth && !isAuthenticated) {
    next();
  } else {
    next();
  }
}