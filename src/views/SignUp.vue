<template>
  <div class="modal" :class="{show:showModal}">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Sign Up</h5>
          <button type="button" class="close-btn" @click="closeModal">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <form @submit.prevent="submitForm">
          <div class="modal-body">
            <div class="form-group">
              <label for="inputId">ID</label>
              <input type="text" class="form-control" v-model="id" required>
            </div>
            <div class="form-group">
              <label for="inputPassword">Password</label>
              <input type="password" class="form-control" v-model="password" required>
            </div>
            <div class="form-group">
              <label for="inputSecret">Secret Value</label>
              <input type="password" class="form-control" v-model="secret" required>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeModal">Close</button>
            <button type="submit" class="btn btn-primary">Submit</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
<script>
import axios from "axios";
const api = axios.create({
  baseURL: 'http://localhost:5657'
});
export default {
  name: "sign_up",
  props: {
    showModal: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      id : "",
      password : "",
      secret : "",
    }
  },
  methods: {
    closeModal() {
      this.secret = null;
      let result = {
        inputId : this.id,
        inputPassword : this.password,
        showModal : false,
      }
      this.$emit("setShowModal", result);
    },
    submitForm() {
      const user = {
        id: this.id,
        password: this.password,
        secret: this.secret
      };
      api.post("/api/v1/user/signup", user)
          .then(response => {
            // Handle success response
            console.log(response.data);
            this.closeModal();
          })
          .catch(error => {
            // Handle error
            console.error(error);
          });
      this.closeModal();
    }
  }
}
</script>
<style lang="scss">
.modal {
  display: none;
  position: fixed;
  z-index: 9999;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  overflow: auto;
  background-color: rgba(0, 0, 0, 0.4);
}

.modal.show {
  display: block;
}

.modal-dialog {
  margin: 15% auto;
  width: 400px;
}

.modal-content {
  background-color: #fefefe;
  padding: 20px;
  border: 1px solid #888;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.modal-title {
  margin: 0;
}

.modal-footer {
  border-top: 1px solid #ddd;
  padding-top: 10px;
  text-align: right;
}
.close-btn {
  position: absolute;
  top: -0px;
  right: -0px;
  width: 30px;
  height: 30px;
  background-color: #fff;
  border: 0;
  cursor: pointer;
  transition: background-color 0.3s ease; /* Apply a smooth transition effect to the background color */
  display: flex;
  justify-content: center;
  align-items: center;
}

.close-btn:hover {
  background-color: #f0f0f0; /* Change the background color on hover for a smooth effect */
}

.close-btn span {
  display: block;
  font-size: 20px;
  line-height: 30px;
  text-align: center;
  color: #333;
  font-weight: bold;
}
</style>