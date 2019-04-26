import Vue from 'vue'
import Router from 'vue-router'
import Homepage from '@/components/Homepage'
import Topology from '@/components/Topology'
import Register from '@/components/Register'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'Homepage',
      component: Homepage
    }, {
      path: '/topology',
      name: 'Topology',
      component: Topology
    }, {
      path: '/register',
      name: 'Register',
      component: Register
    }
  ]
})
