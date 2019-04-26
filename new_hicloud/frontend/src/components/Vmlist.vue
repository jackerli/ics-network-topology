<template>
  <div class="panel">
    <el-menu
      mode="horizontal"
      background-color="#545c64"
      text-color="#fff"
      active-text-color="#ffd04b"
      style="top: 0;">
      <el-menu-item><a v-on:click="skiptoDashboard">Dashboard</a></el-menu-item>
      <el-menu-item><a v-on:click="skiptoCluster">物理集群</a></el-menu-item>
      <el-menu-item><a v-on:click="skiptoVmlist">虚拟机列表</a></el-menu-item>
    </el-menu>
    <div><font size="5">虚拟机列表</font></div>
    <div class="panel-body">
      <table class="table table-hover table-bordered">
        <thead>
        <tr>
          <th>序号</th>
          <th>uuid</th>
          <th>名称</th>
          <th>IP</th>
          <th>所在主机</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
        </thead>
        <tbody v-if="Contents.length">
        <tr v-for="item in Contents" :key="item.id">
          <td>{{item.id}}</td>
          <td>{{item.uuid}}</td>
          <td>{{item.name}}</td>
          <td>{{item.ip_addr}}</td>
          <td>{{item.host_loc}}</td>
          <td>{{item.status}}</td>
          <td>
            <a title="查看详情" role="button" v-on:click="showDetail"><i class="fa fa-list fa-1x"></i></a>
          </td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Vmlist',
  data () {
    return {
      Contents: [
        {id: 1, uuid: 'fad', name: 'test', ip_addr: '127.0.0.1', host_loc: 'test1', status: 'offline'}
      ]
    }
  },
  methods: {
    skiptoCluster: function () {
      let _this = this
      _this.$router.push({path: '/clusterlist'})
    },
    skiptoVmlist: function () {
      let _this = this
      _this.$router.push({path: '/vmlist'})
    },
    skiptoDashboard: function () {
      let _this = this
      _this.$router.push({path: '/dashboard'})
    }
  }
}
</script>

<style scoped>

</style>
