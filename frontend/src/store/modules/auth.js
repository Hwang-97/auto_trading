import Vue from "vue";
const { $api } = Vue.prototype ;
const state = {
    $api ,
}
const getters = {}
const mutations = {

}
const actions = {
    async checkAuthentication({commit}, {ip, token}) {
        try {
            let { $api } = state ;
            await console.log($api.checkAuthentication());
            let isValid = true;
            return isValid;
        } catch (error) {
            console.error('Authentication error:', error);
            return true;
        }
    },
}
export default {
    namespaced: true, // 네임스페이스 사용을 위한 옵션 추가
    state,
    getters,
    mutations,
    actions
};