<template>
  <div id="ClusterList">
    <el-dialog title="虚拟机列表" :visible="Checkdetails" width="50%">
      <el-table :data="vmContents">
        <el-table-column property="id" label="序号" width="150"></el-table-column>
        <el-table-column property="vm_name" label="名称" width="150"></el-table-column>
        <el-table-column property="ip_addr" label="IP" width="150"></el-table-column>
        <el-table-column property="create_time" label="创建时间" width="150"></el-table-column>
        <el-table-column property="status" label="状态" width="150"></el-table-column>
      </el-table>
    </el-dialog>
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
      <div><font size="5">物理集群列表</font></div>
      <div class="panel-body">
        <table class="table table-hover table-bordered">
          <thead>
          <tr>
            <th>序号</th>
            <th>名称</th>
            <th>IP</th>
            <th>CPU</th>
            <th>内存</th>
            <th>磁盘</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
          </thead>
          <tbody v-if="Contents.length">
          <tr v-for="item in Contents" :key="item.id">
            <td>{{item.id}}</td>
            <td>{{item.device_name}}</td>
            <td>{{item.ip_addr}}</td>
            <td><el-progress :text-inside="true" :stroke-width="18" :percentage="item.cpu_usage"></el-progress></td>
            <td>{{item.mem_total}}</td>
            <td>{{item.disk_total}}</td>
            <td>{{item.status}}</td>
            <td>
              <a title="查看详情" role="button" v-on:click="showDetail"><i class="fa fa-list fa-1x"></i></a>
            </td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Clusterlist',
  created () {
    this.Checkdetails = false
  },
  data () {
    return {
      Checkdetails: false,
      Contents: [
        {id: 1, device_name: 'test', ip_addr: '127.0.0.1', cpu_usage: 20, mem_total: 200, disk_total: 200, status: 'offline'}
      ],
      vmContents: [
        {id: 1, vm_name: 'test', ip_addr: '127.0.0.1', create_time: '2019.04.23', status: 'offline'}
      ]
    }
  },
  methods: {
    showDetail: function () {
      let _this = this
      _this.Checkdetails = true
    },
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

<style scoped lang="scss">
@import "../../node_modules/font-awesome/css/font-awesome.min.css";

#ClusterList {
  .clearfix {
    margin: 0 -.5em;

    .col-md-3 {
      padding-left: .5em;
      padding-right: .5em;

      .panel-body {
        padding: .5em 1em;
      }

      .h4 {
        font-size: 140%;
      }
    }
  }

  .form-horizontal .form-group {
    margin-left: 0;
    margin-right: 0;
  }

  .absolute-right {
    position: absolute;
    top: .6em;
    right: 0;
  }

  .datetimepicker {
    padding-left: 1em;
    padding-right: 1em;
  }
}
</style>
