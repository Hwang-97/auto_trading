import axios from 'axios';

const state = {
  user: null
};

const getters = {
  isAuthenticated: state => !!state.user,
  getUser: state => state.user
};

const mutations = {
  setUser(state, user) {
    state.user = user;
  },
  clearUser(state) {
    state.user = null;
  }
};

const actions = {
  loginUser({ commit }, userData) {
    return new Promise((resolve, reject) => {
      axios.post('api/login', userData)
        .then(response => {
          const user = response.data;
          commit('setUser', user);
          resolve();
        })
        .catch(error => {
          commit('clearUser');
          reject(error);
        });
    });
  }
};

export default {
  namespaced: true, // 네임스페이스 사용을 위한 옵션 추가
  state,
  getters,
  mutations,
  actions
};
