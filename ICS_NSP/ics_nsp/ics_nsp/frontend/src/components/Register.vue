<template>
  <div class="div-body">
    <br><br><br><br>
    <div class="container">
      <div class="brand row col-xs-12">
        <div class="tar_title">注册</div>
      </div>
      <div class="content-bottom">
        <form>
          <div class="field-group">
            <span class="fa fa-address-book" aria-hidden="true"></span>
            <div class="wthree-field">
              <input type="text" placeholder="学号" v-model="user.username" required>
            </div>
          </div>
          <div class="field-group">
            <span class="fa fa-user" aria-hidden="true"></span>
            <div class="wthree-field">
              <input type="text" placeholder="用户名" v-model="user.username" required>
            </div>
          </div>
          <div class="field-group">
            <span class="fa fa-lock" aria-hidden="true"></span>
            <div class="wthree-field">
              <input type="Password" placeholder="密码" v-model="user.password" pattern="^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,10}$" required>
            </div>
          </div>
          <div class="field-group">
            <span class="fa fa-unlock" aria-hidden="true"></span>
            <div class="wthree-field">
              <input type="Password" placeholder="确认密码" v-model="user.password_again" pattern="^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,10}$" required>
            </div>
          </div>
          <div class="field-group">
            <span class="fa fa-envelope-o fa-fw" aria-hidden="true"></span>
            <div class="wthree-field">
              <input type="Email" placeholder="邮箱" v-model="user.email" pattern="^[a-zA-Z][0-9a-zA-Z]*@{1}[0-9a-zA-Z]+\.(com|net|cn|com\.cn)$" required>
            </div>
          </div>
          <div class="wthree-field">
            <input type="submit" value="注册" v-on:click="register"/>
          </div>
          <br>
          <div class="wthree-field">
            <input type="submit" value="返回" v-on:click="back"/>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Register',
  data () {
    return {
      user: {
        username: '',
        password: '',
        password_again: '',
        email: ''
      },
      form: {
        username: false,
        password: false,
        password_again: false,
        email: false
      }
    }
  },
  methods: {
    back: function () {
      let _this = this
      _this.$router.push({path: '/'})
    },
    register: function () {
      let _this = this
      if (_this.user.password !== _this.user.password_again) {
        alert('请输入相同的密码')
      } else if (_this.user.password === '' || _this.user.password_again === '' || _this.user.username === '' || _this.user.email === '') {
        _this.user.username === '' ? _this.form.username = true : _this.form.username = false
        _this.user.password === '' ? _this.form.password = true : _this.form.password = false
        _this.user.password_again === '' ? _this.form.password_again = true : _this.form.password_again = false
        _this.user.email === '' ? _this.form.email = true : _this.form.email = false
      } else {
        let userinfo = {username: _this.user.username, password: _this.user.password, email: _this.user.email}
        this.$http.request({
          url: _this.$url + 'api/user/register',
          method: 'POST',
          params: userinfo
        }).then(function (response) {
          if (response.data.code === 100) {
            alert('注册成功，跳转至登录页面！')
            _this.$router.push({path: '/'})
          } else {
            alert(response.data.msg)
          }
        })
      }
    }
  }
}
</script>

<style scoped>
  @import '../assets/css/style.css';
  @import '../assets/css/font-awesome.css';
  @import "../assets/css/homepage.css";
  .tar_title{
    color: #D0D0D0;
    font-size: 30px;
    font-style: normal;
  }
</style>
