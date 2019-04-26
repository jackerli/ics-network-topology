// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import VueRouter from 'vue-router'
import App from './App'
import router from './router'
import axios from 'axios'
import X2js from 'x2js'

Vue.use(VueRouter)

Vue.config.productionTip = false
// axios赋值给变量http
Vue.prototype.$http = axios
Vue.prototype.$url = 'http://127.0.0.1:8000/'
// x2js插件的定义
Vue.prototype.$x2js = new X2js()// 创建x2js对象

/* eslint-disable no-new */
new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>'
})
