import api from "@common/api.js"

export default {
    install(Vue) {
        Vue.prototype.$api = api;
    }
}