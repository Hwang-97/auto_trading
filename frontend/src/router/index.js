import Vue from "vue";
import VueRouter from "vue-router";
import beforeEach from "@/router/beforeEach";
import LoginComponent from "@/views/Login";

Vue.use(VueRouter);

// 중복 라우터 푸시 방지
const originalPush = VueRouter.prototype.push;
VueRouter.prototype.push = function push( location ) {
    return originalPush.call(this, location).catch(( err ) => {
        if (err.name !== 'NavigationDuplicated') throw err;
    });
};

// 중복 라우터 리플레이스 방지
const originalReplace = VueRouter.prototype.replace;
VueRouter.prototype.replace = function replace( location ) {
    return originalReplace.call(this, location).catch(( err ) => {
        if (err.name !== 'NavigationDuplicated') throw err;
    });
};

const routes = [
  {
    path: '/login',
    name: 'Login',
    meta: {
        requiresAuth : true
    },
    component: LoginComponent
  },
  // 다른 경로와 컴포넌트 추가
];

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
});

router.beforeEach(beforeEach);

export default router;