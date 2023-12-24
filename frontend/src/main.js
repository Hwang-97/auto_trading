import Vue from "vue";
import App from '@/App.vue'
import router from "@/router";
import store from "@/store";
import axios from 'axios';
import { BootstrapVue } from  'bootstrap-vue';
import cmmnPlugin from "@/common/cmmnPlugin.js";
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';

Vue.use(BootstrapVue); // BootstrapVue를 전역으로 사용합니다.
Vue.use(cmmnPlugin);   // cmmnPlugin을 전역으로 사용합니다.

new Vue({
  router,
  store,
  render: (h) => h(App),
}).$mount('#app');
