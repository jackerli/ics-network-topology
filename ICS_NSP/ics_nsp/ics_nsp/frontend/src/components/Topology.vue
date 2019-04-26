<template>
  <div class="container">
    <div class="content row">
      <div id="mynetwork" class="canvas col-md-8"></div>
      <div class="panel col-md-4">
        <div class="panel-heading">
          <p><button class="a_demo_one" v-on:click="deployTopo">部署网络</button></p>
        </div>
        <div class="panel-body">
          <table class="table table-hover table-bordered table">
            <thead>
              <tr>
                <th>序号</th>
                <th>设备名称</th>
                <th>设备IP地址</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody v-if="Contents.length">
            <tr v-for="item in Contents" :key="item.id">
              <td>{{item.id}}</td>
              <td>{{item.name}}</td>
              <td>{{item.ip_addr}}</td>
              <td class="text-center">
                <a title="启动" role="button" v-on:click="startVM(item.uuid)"><i class="fa fa-play-circle fa-1x"></i></a>
                <a title="关机" role="button" v-on:click="stopVM(item.uuid)"><i class="fa fa-times-circle-o fa-1x"></i></a>
                <a title="挂起" role="button" v-on:click="pauseVM(item.uuid)"><i class="fa fa-pause-circle fa-1x"></i></a>
                <a title="恢复" role="button" v-on:click="resumeVM(item.uuid)"><i class="fa fa-refresh fa-1x"></i></a>
              </td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as vis from 'vis'
import '../assets/css/vis.css'

export default {
  created: function () {
  },
  data () {
    return {
      nodes: [
        {id: 1, label: 'HMI', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/h5HI3xrx0TaTrHWr4dwVT3ZfXNf4a6VVvRYdTfobRuE!/r/dEcBAAAAAAAA'},
        {id: 2, label: 'PLC', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/E7Asp1C4dBpYeZ3liUMrMkiBpNVihXB2M4zyhaypxmI!/r/dL8AAAAAAAAA'},
        {id: 3, label: 'SWITCH', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/8HlJaXUKdtrmeSo2MoJotp32fPMGYHa9m9174bdx2TY!/r/dL8AAAAAAAAA'},
        {id: 4, label: 'UNITY', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/xFpyx*duKramFE2RhdvJEF1a37YnkYHOxVRGmsbxfqU!/r/dLkAAAAAAAAA'},
        {id: 5, label: 'AD', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/i4XTRabOwufKIwGcpeBISBHoqH4*b2Qv091.OMNBdsQ!/r/dFQBAAAAAAAA'},
        {id: 6, label: 'FIREWALL1', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/WL8F*rprl8h2mXej2Bw0bwEnZAIZzuAtHDEWGB795cc!/r/dDUBAAAAAAAA'},
        {id: 7, label: 'FIREWALL2', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/WL8F*rprl8h2mXej2Bw0bwEnZAIZzuAtHDEWGB795cc!/r/dDUBAAAAAAAA'},
        {id: 8, label: 'FIREWALL3', image: 'http://r.photo.store.qq.com/psb?/V11cZr0n3DvBTH/WL8F*rprl8h2mXej2Bw0bwEnZAIZzuAtHDEWGB795cc!/r/dDUBAAAAAAAA'}
      ],
      edges: [
        {from: 1, to: 6},
        {from: 6, to: 3},
        {from: 3, to: 6},
        {from: 3, to: 7},
        {from: 3, to: 8},
        {from: 7, to: 2},
        {from: 8, to: 4},
        {from: 5, to: 3}
      ],
      Contents: [],
      user: {
        username: ''
      }
    }
  },
  methods: {
    // 一键部署网络
    deployTopo: function () {
      let _this = this
      const xmlhttp = new XMLHttpRequest()
      xmlhttp.open('GET', '../../static/topology.xml', false)
      xmlhttp.send()
      var xmlDoc = xmlhttp.responseText
      var xmlparam = {'xmlTopo': xmlDoc.toString()}
      this.$http.request({
        url: _this.$url + 'api/topology/deployTopo',
        method: 'POST',
        params: xmlparam
      }).then(function (response) {
        console.log(response)
        if (response.code === 100 && response.data.list) {
          // 获取各个设备的信息
          this.Contents = response.data.list
          alert('部署成功！')
        } else {
          alert('部署失败，请联系管理员！')
        }
      })
    },
    // 根据参数uuid启动虚拟机
    startVM: function (uuid) {
      let _this = this
      let vmparams = {uuid: uuid}
      this.$http.request({
        url: _this.$url + 'api/topology/startVM',
        method: 'POST',
        params: vmparams
      }).then(function (response) {
        if (response.data.code === 100) {
          console.log('启动成功')
        } else {
          alert('启动失败，请联系管理员')
        }
      })
    },
    // 根据参数uuid关闭虚拟机
    stopVM: function (uuid) {
      let _this = this
      let vmparams = {uuid: uuid}
      this.$http.request({
        url: _this.$url + 'api/topology/stopVM',
        method: 'POST',
        params: vmparams
      }).then(function (response) {
        if (response.data.code === 100) {
          console.log('关闭成功')
        } else {
          alert('关闭失败，请联系管理员')
        }
      })
    },
    // 根据参数uuid挂起虚拟机
    pauseVM: function (uuid) {
      let _this = this
      let vmparams = {uuid: uuid}
      this.$http.request({
        url: _this.$url + 'api/topology/pauseVM',
        method: 'POST',
        params: vmparams
      }).then(function (response) {
        if (response.data.code === 100) {
          console.log('挂起成功')
        } else {
          alert('挂起失败，请联系管理员')
        }
      })
    },
    // 根据参数uuid恢复虚拟机
    resumeVM: function (uuid) {
      let _this = this
      let vmparams = {uuid: uuid}
      this.$http.request({
        url: _this.$url + 'api/topology/resumeVM',
        method: 'POST',
        params: vmparams
      }).then(function (response) {
        if (response.data.code === 100) {
          console.log('恢复成功')
        } else {
          alert('恢复失败，请联系管理员')
        }
      })
    },
    cavs () {
      var nodes = new vis.DataSet(this.nodes)
      var edges = new vis.DataSet(this.edges)
      var container = document.getElementById('mynetwork')
      var data = {
        nodes: nodes,
        edges: edges
      }
      var options = {
        // autoResize: false,
        nodes: {
          shape: 'image'
        },
        edges: {
          color: {
            color: '#4C5967',
            highlight: '#4C5967',
            hover: '#4C5967'
          },
          length: 200,
          width: 2,
          // selectionWidth: 0,
          // hoverWidth: 0,
          font: {
            size: 12,
            strokeWidth: 0
          },
          smooth: {
            enabled: false,
            type: 'cubicBezier',
            roundness: 0.8
          }
        },
        // 关闭物理引擎
        physics: {
          enabled: false
        },
        layout: {
          randomSeed: 9
        },
        interaction: {
          dragNodes: true, // 是否能拖动节点
          dragView: true, // 是否能拖动画布
          hover: true, // 鼠标移过后加粗该节点和连接线
          multiselect: true, // 按 ctrl 多选
          selectable: true, // 是否可以点击选择
          selectConnectedEdges: true, // 选择节点后是否显示连接线
          hoverConnectedEdges: true, // 鼠标滑动节点后是否显示连接线
          zoomView: true // 是否能缩放画布
        },
        manipulation: {
          enabled: false,
          addEdge: (edge, callback) => {
            this.isClosedLine(edge)
          }
        }
      }
      this.network = new vis.Network(container, data, options)
      this.network.on('selectNode', function (params) {

      })
    }
  },
  mounted () {
    this.cavs()
  }
}
</script>

<style>
  @import '../assets/css/style.css';
  @import '../assets/css/font-awesome.css';
  @import "../assets/css/homepage.css";
  *{
    margin: 0;
    padding: 0;
  }
  [type=button] {
    -webkit-appearance: button;
  }

  .canvas{
    margin-left: 0;
    height: 600px;
    background: #808695;
    margin-top: 0px;
  }
  .data p:first-child{
    margin-bottom: 5px;
  }
  .a_demo_one {
    background-color:#3bb3e0;
    padding:10px;
    position:relative;
    font-family: 'Open Sans', sans-serif;
    font-size:12px;
    text-decoration:none;
    color:#fff;
    border: solid 1px #186f8f;
    background-image: linear-gradient(bottom, rgb(44,160,202) 0%, rgb(62,184,229) 100%);
    background-image: -o-linear-gradient(bottom, rgb(44,160,202) 0%, rgb(62,184,229) 100%);
    background-image: -moz-linear-gradient(bottom, rgb(44,160,202) 0%, rgb(62,184,229) 100%);
    background-image: -webkit-linear-gradient(bottom, rgb(44,160,202) 0%, rgb(62,184,229) 100%);
    background-image: -ms-linear-gradient(bottom, rgb(44,160,202) 0%, rgb(62,184,229) 100%);
    background-image: -webkit-gradient(
      linear,
      left bottom,
      left top,
      color-stop(0, rgb(44,160,202)),
      color-stop(1, rgb(62,184,229))
    );
    -webkit-box-shadow: inset 0px 1px 0px #7fd2f1, 0px 1px 0px #fff;
    -moz-box-shadow: inset 0px 1px 0px #7fd2f1, 0px 1px 0px #fff;
    box-shadow: inset 0px 1px 0px #7fd2f1, 0px 1px 0px #fff;
    -webkit-border-radius: 5px;
    -moz-border-radius: 5px;
    -o-border-radius: 5px;
    border-radius: 5px;
  }

  .a_demo_one:active {
    padding-bottom:9px;
    padding-left:10px;
    padding-right:10px;
    padding-top:11px;
    top:1px;
    background-image: linear-gradient(bottom, rgb(62,184,229) 0%, rgb(44,160,202) 100%);
    background-image: -o-linear-gradient(bottom, rgb(62,184,229) 0%, rgb(44,160,202) 100%);
    background-image: -moz-linear-gradient(bottom, rgb(62,184,229) 0%, rgb(44,160,202) 100%);
    background-image: -webkit-linear-gradient(bottom, rgb(62,184,229) 0%, rgb(44,160,202) 100%);
    background-image: -ms-linear-gradient(bottom, rgb(62,184,229) 0%, rgb(44,160,202) 100%);
    background-image: -webkit-gradient(
      linear,
      left bottom,
      left top,
      color-stop(0, rgb(62,184,229)),
      color-stop(1, rgb(44,160,202))
    );
  }

</style>
