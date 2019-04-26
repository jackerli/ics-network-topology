<template >
  <div class="bgimage">
    <el-form label-position="left" label-width="0px" class="demo-ruleForm login-container">
      <h3 class="title">云管理平台</h3>
      <el-form-item prop="account">
        <el-input type="text" v-model="user.username" auto-complete="off" placeholder="账号"></el-input>
      </el-form-item>
      <el-form-item prop="checkPass">
        <el-input type="password" v-model="user.password" auto-complete="off" placeholder="密码"></el-input>
      </el-form-item>
      <el-form-item style="width:100%;">
        <el-button type="primary" style="width:100%;" v-on:click="login">登录</el-button>
      </el-form-item>
    </el-form>
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
    login: function () {
      let _this = this
      let userparams = {username: _this.user.username, password: _this.user.password}
      if (this.user.username === '' || this.user.password === '') {
        console.log('Empty Form!')
      } else {
        this.$http.request({
          url: _this.$url + 'api/usermanager/login_check',
          method: 'POST',
          params: userparams
        }).then(function (response) {
          console.log(response.data.code)
          if (response.data.code === 100) {
            _this.$router.push({path: '/dashboard'})
          } else {
            alert(response.data.msg)
            _this.$router.push({path: '/'})
          }
        })
      }
    }
  }
}
</script>

<style>
  .bgimage {
    background-image: url("../assets/images/cloud.jpg");
    top: 0;
    left: 0;
    position: fixed;
    width: 100%;
    height: 100%;
    background-size: cover;
    -webkit-background-size: cover;
    -moz-background-size: cover;
    -o-background-size: cover;
    -ms-background-size: cover;
    background-attachment: fixed;
    font-family: 'Mukta Mahee', sans-serif;
  }
  .login-container {
    /*box-shadow: 0 0px 8px 0 rgba(0, 0, 0, 0.06), 0 1px 0px 0 rgba(0, 0, 0, 0.02);*/
    -webkit-border-radius: 5px;
    border-radius: 5px;
    -moz-border-radius: 5px;
    background-clip: padding-box;
    margin: 180px auto;
    width: 350px;
    padding: 35px 35px 15px 35px;
    background: #fff;
    border: 1px solid #eaeaea;
    box-shadow: 0 0 25px #cac6c6;
  }
  .title {
    margin: 0px auto 40px auto;
    text-align: center;
    color: #505458;
  }
  .remember {
    margin: 0px 0px 35px 0px;
  }
</style>
