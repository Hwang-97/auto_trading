<template>
  <div class="login-container">
    <div class="login-box">
      <h2 class="mb-4">Login</h2>
      <form @submit.prevent="login" class="login-form">
        <div class="form-group">
          <label for="username" class="font-weight-bold">Username:</label>
          <input type="text" id="username" v-model="username" required class="form-control">
        </div>
        <div class="form-group">
          <label for="password" class="font-weight-bold">Password:</label>
          <input type="password" id="password" v-model="password" required class="form-control">
        </div>
        <button type="submit" class="btn btn-primary btn-block">Login</button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      username: '',
      password: ''
    };
  },
  methods: {
    login() {
      const userData = {
        username: this.username,
        password: this.password
      };

      this.$store.dispatch('user/loginUser', userData)
        .then(() => {
          this.$router.push('/home');
        })
        .catch(error => {
          console.error(error);
          // Handle error
        });
    }
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

.login-box {
  width: 300px;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.login-form .form-group {
  margin-bottom: 15px;
}

.login-form label {
  font-weight: bold;
}

.login-form .form-control {
  width: 100%;
}

.btn-block {
  display: block;
  width: 100%;
}
</style>
