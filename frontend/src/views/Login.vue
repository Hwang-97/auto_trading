<template>
  <div>
    <!-- 로그인 폼 -->
    <div class="login-container">
      <form id="login-form"
            @submit.prevent="submitForm"
            class="login-form"
            :style="{ transform: formTransform, transition: formTransition }">
        <div class="form-group">
          <label for="inputId">ID</label>
          <input type="text" class="form-control" id="inputId" v-model="id" required>
        </div>
        <div class="form-group">
          <label for="inputPassword">Password</label>
          <input type="password" class="form-control" id="inputPassword" v-model="password" required>
        </div>
        <br>
        <button type="submit" class="btn btn-primary" style="margin-right: 10px;">Login</button>
        <button class="btn btn-primary signup-btn" @click.prevent="openModal">Sign Up</button>
      </form>
    </div>
    <!-- SignUp 컴포넌트 호출 -->
    <SignUp :showModal="showModal"
            @setShowModal="setShowModal"
            :style="{ transform: formTransform, transition: formTransition }">
    </SignUp>
  </div>
</template>

<script>
import axios from "axios";
import SignUp from "@views/SignUp";

const api = axios.create({
  baseURL: 'http://localhost:5657'
});
export default {
  data() {
    return {
      showModal: false,
       id: '',
       password: '',
       secret: '',
       isDragging: false,
       dragStartX: 0,
       dragStartY: 0,
       formTransform: 'none',
       formTransition: 'none',
       // 특정 아이피일 경우에만 동작하도록 처리할 변수
       specialIP: '1232',
    };
  },
  components: {
    SignUp
  },
  async mounted() {
    // console.log(valueToEncrypt);
    if (!this.isSpecialIP()) {
      this.moveFormRandomly();
    }
  },
  methods: {
    openModal() {
      this.showModal = true;
    },
    setShowModal(object){
      this.password = object.inputPassword;
      this.id = object.inputId;
      this.showModal = object.showModal;
    },
    moveFormRandomly() {
      const container = document.querySelector('#login-form');
      if (!container) return;

      const maxX = window.innerWidth;
      const maxY = window.innerHeight;

      // 공의 반지름을 고려하여 x, y 좌표를 설정
      const randomX = Math.floor(Math.random() * (maxX) - 1000);
      const randomY = Math.floor(Math.random() * (maxY) - 400);

      this.formTransform = `translate(${randomX}px, ${randomY}px)`;
      this.formTransition = 'transform 0.05s ease';

      // 폼을 계속 움직이도록 반복 호출
      requestAnimationFrame(this.moveFormRandomly);
    },
    isSpecialIP() {
      // 현재 클라이언트 IP가 특정 아이피인지 확인하는 로직
      // 여기에서 특정 아이피를 체크하는 로직을 구현하면 됩니다.
      return this.getClientIP() === this.specialIP;
    },
    getClientIP() {
      return this.$api.getClientIP();
    },
    submitForm() {
      // 폼 제출 로직
    },
  }
};
</script>

<style lang="scss">
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

/* 로그인 폼 스타일 */
.login-form {
  max-width: 400px;
  padding: 20px;
  border: 1px solid #ccc;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.login-form label {
  font-weight: bold;
}

.login-form input[type="text"],
.login-form input[type="password"] {
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.login-form button {
  padding: 10px 20px;
  border-radius: 4px;
}

.signup-btn {
  background-color: #007bff; /* 또는 원하는 색상으로 변경 */
}

.signup-btn:hover {
  background-color: #0056b3; /* 또는 원하는 색상으로 변경 */
}
</style>
