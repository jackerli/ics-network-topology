<template>
  <div class="div-body">
    <div class="container">
      <div class="brand row col-xs-12">
        <div class="tar_title">网络安全实训系统</div>
      </div>
      <div class="content row">
        <div class="notice col-md-5 col-xs-12" style="margin-top: 10%">
          <div class="panel panel-primary ">
            <div class="panel-heading">
              使用须知
            </div>
            <div class="panel-body">
              <p align="left">1.请使用真实姓名注册</p>
              <p align="left">2.请使用北航邮箱进行注册</p>
              <p align="left">3.请仔细阅读课程注意事项</p>
              <p align="left">4.请仔细确认网络拓扑结构，中途无法更改</p>
              <p align="left">5.如有问题，请联系：13121239987@163.com</p>
            </div>
          </div>
        </div>
        <div class=" col-md-6 col-md-offset-1" style="margin-top: 3%">
          <div class="content-w3ls" style="max-width: 480px">
            <div class="content-bottom">
              <form>
                <div class="field-group">
                  <span class="fa fa-user" aria-hidden="true"></span>
                  <div class="wthree-field">
                    <input type="text" placeholder="用户名" v-model="user.username" required>
                  </div>
                </div>
                <div class="field-group">
                  <span class="fa fa-lock" aria-hidden="true"></span>
                  <div class="wthree-field">
                    <input type="Password" placeholder="密码" v-model="user.password" required>
                  </div>
                </div>
                <div class="wthree-field">
                  <input type="submit" value="登录" v-on:click="login"/>
                </div>
                <ul class="list-login">
                  <li>
                    <a class="text-left" v-on:click="register">注册&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</a>
                    <a class="text-right">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;忘记密码？</a> +
                  </li>
                </ul>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Homepage',
  data () {
    return {
      user: {
        username: '',
        password: ''
      }
    }
  },
  methods: {
    register: function () {
      let _this = this
      _this.$router.push({path: '/register'})
    },
    login: function () {
      let _this = this
      let userparams = {username: _this.user.username, password: _this.user.password}
      if (this.user.username === '' || this.user.password === '') {
        console.log('Empty Form!')
      } else {
        this.$http.request({
          url: _this.$url + 'api/user/login_check',
          method: 'POST',
          params: userparams
        }).then(function (response) {
          console.log(response.data.code)
          if (response.data.code === 100) {
            _this.$router.push({path: '/topology'})
          } else {
            console.log(response.data)
            alert(response.data.msg)
            _this.$router.push({path: '/'})
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
    color: #000000;
    font-size: 30px;
    font-style: normal;
  }
</style>
