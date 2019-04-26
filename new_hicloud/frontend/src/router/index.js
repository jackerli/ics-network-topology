import Vue from 'vue'
import Router from 'vue-router'
import Homepage from '@/components/Homepage'
import Dashboard from '@/components/Dashboard'
import Clusterlist from '@/components/Clusterlist'
import Vmlist from '@/components/Vmlist'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'Homepage',
      component: Homepage
    }, {
      path: '/dashboard',
      name: 'Dashboard',
      component: Dashboard
    }, {
      path: '/clusterlist',
      name: 'Clusterlist',
      component: Clusterlist
    }, {
      path: '/vmlist',
      name: 'Vmlist',
      component: Vmlist
    }
  ]
})
