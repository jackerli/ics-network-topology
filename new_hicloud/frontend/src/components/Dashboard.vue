<template>
  <div >
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
    <div>
      <li class="list-group-item">
        <div><font size="5">物理集群信息</font></div>
        <div class="col-md-12">
          <div class="list-group-item">
            <tr>
              <td><div class="col-md-3">开机数</div></td>
              <td><div class="col-md-3">{{clusterInfo.clusterOn}}</div></td>
              <td><div class="col-md-3">关机数</div></td>
              <td><div class="col-md-3">{{clusterInfo.clusterOff}}</div></td>
            </tr>
          </div>
          <div class="list-group-item">
            <tr>
              <td><div id="clusterChart1" style="width: 500px; height: 300px;"></div></td>
              <td><div id="clusterChart2" style="width: 500px; height: 300px;"></div></td>
              <td><div id="clusterChart3" style="width: 500px; height: 300px;"></div> </td>
            </tr>
          </div>
        </div>
      </li>
      <li class="list-group-item">
        <div><font size="5">虚拟机信息</font></div>
        <div class="col-md-12">
          <div class="list-group-item">
            <tr>
              <td><div class="col-md-2">个数</div></td>
              <td><div class="col-md-2">{{vmInfo.total_num}}</div></td>
              <td><div class="col-md-2">内存总量</div></td>
              <td><div class="col-md-2">{{vmInfo.mem_total}}</div></td>
              <td><div class="col-md-2">磁盘总量</div></td>
              <td><div class="col-md-2">{{vmInfo.disk_total}}</div></td>
            </tr>
          </div>
          <div class="list-group-item">
            <div class="col-sm-2">CPU</div>
            <el-progress :text-inside="true" :stroke-width="18" :percentage="vmInfo.cpu_usage"></el-progress>
          </div>
        </div>
      </li>
    </div>
  </div>
</template>

<script>
import echarts from 'echarts'
export default {
  name: 'Dashboard',
  created () {
    this.refreshClusterinfo()
    this.refreshVminfo()
  },
  data () {
    return {
      clusterInfo: {
        clusterOn: 0,
        clusterOff: 0,
        cpu_usage: 12,
        mem_usage: 90,
        disk_usage: 23,
        mem_total: 100,
        disk_total: 100
      },
      vmInfo: {
        total_num: 0,
        mem_total: 0,
        cpu_usage: 20,
        disk_total: 0
      }
    }
  },
  methods: {
    refreshCharts: function () {
      // CPU占用率饼图实例
      var clusterChart1 = echarts.init(document.getElementById('clusterChart1'))
      var option1 = {
        title: {
          text: 'CPU占用率',
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: '{a}<br/>{b} : {c} ({d}%)'
        },
        series: [
          {
            type: 'pie',
            radius: '65%',
            center: ['50%', '50%'],
            selectedMode: 'single',
            data: [
              {
                backgroundColor: '#eee',
                borderColor: '#777',
                borderWidth: 1,
                borderRadius: 4,
                rich: {
                  title: {
                    color: '#eee',
                    align: 'center'
                  },
                  abg: {
                    backgroundColor: '#333',
                    width: '100%',
                    align: 'right',
                    height: 25,
                    borderRadius: [4, 4, 0, 0]
                  },
                  hr: {
                    borderColor: '#777',
                    width: '100%',
                    borderWidth: 0.5,
                    height: 0
                  },
                  value: {
                    width: 20,
                    padding: [0, 20, 0, 30],
                    align: 'left'
                  },
                  valueHead: {
                    color: '#333',
                    width: 20,
                    padding: [0, 20, 0, 30],
                    align: 'center'
                  },
                  rate: {
                    width: 40,
                    align: 'right',
                    padding: [0, 10, 0, 0]
                  },
                  rateHead: {
                    color: '#333',
                    width: 40,
                    align: 'center',
                    padding: [0, 10, 0, 0]
                  }
                }
              },
              {value: this.clusterInfo.cpu_usage, name: '已使用'},
              {value: 100 - this.clusterInfo.cpu_usage, name: '未使用'}
            ],
            itemStyle: {
              emphasis: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      }
      if (option1 && typeof option1 === 'object') {
        clusterChart1.setOption(option1, true)
      }
      // 内存占用饼图实例
      var clusterChart2 = echarts.init(document.getElementById('clusterChart2'))
      var option2 = {
        title: {
          text: '内存占用',
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: '{a}<br/>{b} : {c} ({d}%)'
        },
        series: [
          {
            type: 'pie',
            radius: '65%',
            center: ['50%', '50%'],
            selectedMode: 'single',
            data: [
              {
                backgroundColor: '#eee',
                borderColor: '#777',
                borderWidth: 1,
                borderRadius: 4,
                rich: {
                  title: {
                    color: '#eee',
                    align: 'center'
                  },
                  abg: {
                    backgroundColor: '#333',
                    width: '100%',
                    align: 'right',
                    height: 25,
                    borderRadius: [4, 4, 0, 0]
                  },
                  hr: {
                    borderColor: '#777',
                    width: '100%',
                    borderWidth: 0.5,
                    height: 0
                  },
                  value: {
                    width: 20,
                    padding: [0, 20, 0, 30],
                    align: 'left'
                  },
                  valueHead: {
                    color: '#333',
                    width: 20,
                    padding: [0, 20, 0, 30],
                    align: 'center'
                  },
                  rate: {
                    width: 40,
                    align: 'right',
                    padding: [0, 10, 0, 0]
                  },
                  rateHead: {
                    color: '#333',
                    width: 40,
                    align: 'center',
                    padding: [0, 10, 0, 0]
                  }
                }
              },
              {value: this.clusterInfo.mem_usage, name: '已占用'},
              {value: this.clusterInfo.mem_total - this.clusterInfo.mem_usage, name: '剩余'}
            ],
            itemStyle: {
              emphasis: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      }
      if (option2 && typeof option2 === 'object') {
        clusterChart2.setOption(option2, true)
      }
      // 磁盘占用饼图实例
      var clusterChart3 = echarts.init(document.getElementById('clusterChart3'))
      var option3 = {
        title: {
          text: '磁盘占用',
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: '{a}<br/>{b} : {c} ({d}%)'
        },
        series: [
          {
            type: 'pie',
            radius: '65%',
            center: ['50%', '50%'],
            selectedMode: 'single',
            data: [
              {
                backgroundColor: '#eee',
                borderColor: '#777',
                borderWidth: 1,
                borderRadius: 4,
                rich: {
                  title: {
                    color: '#eee',
                    align: 'center'
                  },
                  abg: {
                    backgroundColor: '#333',
                    width: '100%',
                    align: 'right',
                    height: 25,
                    borderRadius: [4, 4, 0, 0]
                  },
                  hr: {
                    borderColor: '#777',
                    width: '100%',
                    borderWidth: 0.5,
                    height: 0
                  },
                  value: {
                    width: 20,
                    padding: [0, 20, 0, 30],
                    align: 'left'
                  },
                  valueHead: {
                    color: '#333',
                    width: 20,
                    padding: [0, 20, 0, 30],
                    align: 'center'
                  },
                  rate: {
                    width: 40,
                    align: 'right',
                    padding: [0, 10, 0, 0]
                  },
                  rateHead: {
                    color: '#333',
                    width: 40,
                    align: 'center',
                    padding: [0, 10, 0, 0]
                  }
                }
              },
              {value: this.clusterInfo.disk_usage, name: '已占用'},
              {value: this.clusterInfo.disk_total - this.clusterInfo.disk_usage, name: '剩余'}
            ],
            itemStyle: {
              emphasis: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      }
      if (option3 && typeof option3 === 'object') {
        clusterChart3.setOption(option3, true)
      }
    },
    refreshClusterinfo: function () {
      let _this = this
      this.$http.request({
        url: _this.$url + 'api/dashboard/get_phy_mac_info',
        method: 'GET'
      }).then(function (response) {
        if (response.data.code === 100) {
          console.log('Refresh Success!')
        } else {
          console.log('Refresh Error: Please contact the administrator!')
        }
      })
    },
    refreshVminfo: function () {
      let _this = this
      this.$http.request({
        url: _this.$url + 'api/dashboard/get_vir_mac_info',
        method: 'GET'
      }).then(function (response) {
        if (response.data.code === 100) {
          console.log('Refresh Success!')
        } else {
          console.log('Refresh Error: Please contact the administrator!')
        }
      })
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
  },
  mounted () {
    // 初始化echarts实例
    this.refreshCharts()
    this.refreshClusterinfo()
    this.refreshVminfo()
  }
}
</script>

<style scoped>
</style>
