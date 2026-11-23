/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import type { Instance } from 'tippy.js';

import { retrieveDorisInstance } from '@services/source/doris';
import { retrieveEsInstance } from '@services/source/es';
import { retrieveHdfsInstance } from '@services/source/hdfs';
import { retrieveKafkaInstance } from '@services/source/kafka';
import { retrieveMongoInstanceDetail } from '@services/source/mongodb';
import { retrieveOracleHaInstance } from '@services/source/oracleHaCluster';
import { retrievePulsarInstance } from '@services/source/pulsar';
import { retrieveQdrantHaInstanceDetail } from '@services/source/qdrantHa';
import { retrieveRedisInstance } from '@services/source/redis';
import { retrieveRiakInstance } from '@services/source/riak';
import { retrieveSqlserverHaInstance } from '@services/source/sqlserveHaCluster';
import { retrieveSqlserverSingleInstance } from '@services/source/sqlserverSingleCluster';
import { retrieveSurrealdbHaInstanceDetail } from '@services/source/surrealdbHa';
import { retrieveSurrealdbSingleInstanceDetail } from '@services/source/surrealdbSingle';
import { getTendbclusterInstanceDetail } from '@services/source/tendbcluster';
import { retrieveTendbhaInstance } from '@services/source/tendbha';
import { retrieveTendbsingleInstance } from '@services/source/tendbsingle';
import { retrieveVictoriametricsClusterInstanceDetail } from '@services/source/victoriametricsCluster';
import { retrieveVictoriametricsSelectInstanceDetail } from '@services/source/victoriametricsSelect';
import type { ResourceTopo } from '@services/types';

import { ClusterTypes } from '@common/const';
import { ipPort } from '@common/regex';
import { dbTippy } from '@common/tippy';

import {
  ExtensionCategory,
  Graph,
  type GraphData as GraphDataG6,
  type IElementEvent,
  type NodeData,
  NodeEvent,
  register,
} from '@antv/g6';

import { GraphData, type GraphLine, type GraphNode, GroupTypes, type NodeConfig } from './graphData';
import { TopoNode } from './topoNode';

const apiMap = {
  [ClusterTypes.DORIS]: retrieveDorisInstance,
  [ClusterTypes.ES]: retrieveEsInstance,
  [ClusterTypes.HDFS]: retrieveHdfsInstance,
  [ClusterTypes.KAFKA]: retrieveKafkaInstance,
  [ClusterTypes.MONGO_REPLICA_SET]: retrieveMongoInstanceDetail,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: retrieveMongoInstanceDetail,
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: retrieveOracleHaInstance,
  // [ClusterTypes.REDIS_CLUSTER]: retrieveRedisInstance,
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: retrieveRedisInstance,
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: retrieveRedisInstance,
  [ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE]: retrieveRedisInstance,
  [ClusterTypes.PULSAR]: retrievePulsarInstance,
  [ClusterTypes.REDIS_INSTANCE]: retrieveRedisInstance,
  [ClusterTypes.RIAK]: retrieveRiakInstance,
  [ClusterTypes.SQLSERVER_HA]: retrieveSqlserverHaInstance,
  [ClusterTypes.SQLSERVER_SINGLE]: retrieveSqlserverSingleInstance,
  [ClusterTypes.TENDBCLUSTER]: getTendbclusterInstanceDetail,
  [ClusterTypes.TENDBHA]: retrieveTendbhaInstance,
  [ClusterTypes.TENDBSINGLE]: retrieveTendbsingleInstance,
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: retrieveRedisInstance,
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: retrieveRedisInstance,
};

const k8sApiMap = {
  [ClusterTypes.K8S_QDRANT_HA]: retrieveQdrantHaInstanceDetail,
  [ClusterTypes.K8S_SURREALDB_HA]: retrieveSurrealdbHaInstanceDetail,
  [ClusterTypes.K8S_SURREALDB_SINGLE]: retrieveSurrealdbSingleInstanceDetail,
  [ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER]: retrieveVictoriametricsClusterInstanceDetail,
  [ClusterTypes.K8S_VICTORIAMETRICS_SELECT]: retrieveVictoriametricsSelectInstanceDetail,
};

type TopoNodeData = ResourceTopo['nodes'][number];

interface ClusterTopoProps {
  clusterData: {
    bk_biz_id?: number;
    cluster_name: string;
    cluster_type?: string;
    id: number;
    is_public?: boolean;
    isOffline: boolean;
    k8s_cluster_name?: string;
    namespace?: string;
  };
  // 拓扑图支持的集群类型多于详情接口，未登记详情接口的类型（如 Oracle 单机）悬停不展示详情
  clusterType: string;
  dbType: string;
  nodeConfig?: NodeConfig;
}

/** 离开节点后延迟关闭浮层，留出鼠标移入浮层的时间 */
const TIPS_HIDE_DELAY = 150;

register(ExtensionCategory.NODE, 'topo-node', TopoNode);

export const useRenderGraph = (props: ClusterTopoProps) => {
  let graphInstance: Graph | null = null;
  let tippyInstance: Instance | undefined;
  let tipsHideTimer: ReturnType<typeof setTimeout> | undefined;
  // render 是异步的，渲染完成前不处理尺寸变化
  let isGraphRendered = false;

  const instState = reactive<{
    activeId: string;
    detailsCaches: Map<string, any>;
    loadingIds: Set<string>;
    nodeData: TopoNodeData | null;
  }>({
    activeId: '',
    detailsCaches: new Map(),
    loadingIds: new Set(),
    nodeData: null,
  });

  const instDetails = computed(() => instState.detailsCaches.get(instState.activeId));
  // 按实例区分 loading，避免先发出的请求结束时关掉当前实例的 loading
  const isInstLoading = computed(() => instState.loadingIds.has(instState.activeId));

  const isK8sCluster = computed(() => props.clusterType in k8sApiMap);
  const hasDetailApi = computed(() => props.clusterType in apiMap || isK8sCluster.value);

  /**
   * 是否为可查看详情的实例行：K8s 为 Pod 行（排除访问入口），其余为 ip:port 实例
   */
  const isInstanceNode = (node: GraphNode) => {
    if (!hasDetailApi.value || node.type !== GroupTypes.NODE) {
      return false;
    }
    if (isK8sCluster.value) {
      return !(node.data as TopoNodeData).node_type.startsWith('entry_');
    }
    return ipPort.test(node.id);
  };

  /**
   * 关闭节点详情浮层（destroy 会同步触发 onHidden，把内容放回模板）
   */
  const hideTips = () => {
    clearTimeout(tipsHideTimer);
    tippyInstance?.destroy();
    tippyInstance = undefined;
  };

  const delayHideTips = () => {
    clearTimeout(tipsHideTimer);
    tipsHideTimer = setTimeout(hideTips, TIPS_HIDE_DELAY);
  };

  const handleNodePointerEnter = (e: IElementEvent) => {
    const { data: node } = e.target as unknown as { data: GraphNode };
    if (!isInstanceNode(node)) {
      return;
    }

    // 上一个浮层还在延迟关闭中时，内容仍挂在浮层里，需先关闭让内容回到模板
    hideTips();
    const template = document.getElementById('node-details-tips');
    const content = template?.querySelector('.node-details');
    if (!content || !graphInstance) {
      return;
    }

    // 以节点完整矩形为参照，左侧空间不足翻转到右侧时贴着节点右边缘，不会盖住节点
    const { height, width, x, y } = node.style;
    const [left, top] = graphInstance.getClientByCanvas([x - width / 2, y - height / 2]);
    const [right, bottom] = graphInstance.getClientByCanvas([x + width / 2, y + height / 2]);
    const referenceRect = {
      bottom,
      height: bottom - top,
      left,
      right,
      top,
      width: right - left,
      x: left,
      y: top,
    };
    // 浮层先以 loading 态定位，详情返回后内容变高，tippy 不会自动重新定位，
    // 被视口挤压后箭头仍停在旧位置，需监听内容尺寸变化手动更新定位
    const resizeObserver = new ResizeObserver(() => {
      tippyInstance?.popperInstance?.update();
    });
    const tippy = dbTippy(document.body, {
      allowHTML: true,
      // 全屏时只渲染全屏元素内的节点，浮层需挂到全屏元素下才可见
      appendTo: () => (document.fullscreenElement as HTMLElement | null) || document.body,
      arrow: true,
      content,
      getReferenceClientRect: () => referenceRect as DOMRect,
      hideOnClick: false,
      interactive: true,
      maxWidth: 320,
      onDestroy: () => resizeObserver.disconnect(),
      onHidden: () => template?.append?.(content),
      placement: 'left-start',
      theme: 'light',
      // 显隐完全由节点与浮层的鼠标事件控制
      trigger: 'manual',
      zIndex: 9999,
    });
    // 鼠标移入浮层时保持展示，便于点击「更多详情」，移出后再关闭
    tippy.popper.addEventListener('mouseenter', () => clearTimeout(tipsHideTimer));
    tippy.popper.addEventListener('mouseleave', delayHideTips);
    tippy.show();
    tippyInstance = tippy;
    resizeObserver.observe(content);

    const nodeData = node.data as TopoNodeData;
    instState.activeId = node.id;
    instState.nodeData = nodeData;
    // 未缓存且未在请求中才发请求，请求失败后再次悬停可重试
    if (!instState.detailsCaches.has(node.id) && !instState.loadingIds.has(node.id)) {
      fetchInstDetails(nodeData);
    }
  };

  const handleNodePointerLeave = (e: IElementEvent) => {
    const { data: node } = e.target as unknown as { data: GraphNode };
    if (!isInstanceNode(node)) {
      return;
    }

    delayHideTips();
  };

  const renderDraph = (data: ResourceTopo) => {
    if (props.clusterData.isOffline) {
      return;
    }
    destroyGraph();
    const graphData = new GraphData(props.clusterType, props.nodeConfig).formatGraphData(data, props.dbType);
    const graph = new Graph({
      animation: true,
      // 初始居中不走动画，否则渲染后会有一段从原点平移到中心的移动
      autoFit: { animation: false, type: 'center' },
      behaviors: ['drag-canvas', 'zoom-canvas'],
      container: 'clusterTopoGraphMain',
      data: graphData as unknown as GraphDataG6,
      edge: {
        style: {
          endArrow: true,
          endArrowSize: 5,
          label: true,
          labelAutoRotate: false,
          labelBackground: true,
          labelBackgroundFill: '#fafbfd',
          labelBackgroundLineWidth: 1,
          labelBackgroundRadius: 2,
          labelBackgroundStroke: 'rgba(151, 155, 165, .3)',
          labelFill: '#63656e',
          labelPadding: [2, 8, 0, 8],
          labelPlacement: 'center',
          labelText: (d: any) => d.label,
          stroke: 'rgb(196, 198, 204)',
        },
        // 分组间连线由 graphData 按相对位置指定横向或纵向曲线
        type: (d) => (d as unknown as GraphLine).type || 'cubic-horizontal',
      },
      node: {
        style: {
          fill: '#fff',
          // 端口均为简单端口（不绘制图形），连线固定落在边的中点：
          // 实例行叠放在分组内，上下边被相邻行和分组遮住，只开放左右端口；
          // 分组开放四边中点，具体连哪个端口由 graphData.calcEdgePorts 指定
          ports: (d: NodeData) =>
            (d as unknown as { type: GroupTypes }).type === GroupTypes.NODE
              ? [
                  { key: 'left', placement: 'left' },
                  { key: 'right', placement: 'right' },
                ]
              : [
                  { key: 'top', placement: 'top' },
                  { key: 'bottom', placement: 'bottom' },
                  { key: 'left', placement: 'left' },
                  { key: 'right', placement: 'right' },
                ],
          radius: 4,
          // 实例行在分组内，阴影不可见，只给分组画阴影以减少大集群的绘制开销
          shadowColor: (d: NodeData) =>
            (d as unknown as { type: GroupTypes }).type === GroupTypes.GROUP ? '#1919290d' : 'transparent',
          shadowOffsetX: 2,
          shadowOffsetY: 4,
          size: (d: NodeData) => [d.style!.width as number, d.style!.height as number],
        },
        type: 'topo-node',
      },
    });
    graph.on(NodeEvent.POINTER_ENTER, handleNodePointerEnter);
    graph.on(NodeEvent.POINTER_LEAVE, handleNodePointerLeave);
    graphInstance = graph;
    graph.render().then(() => {
      // 渲染期间图已被重建或销毁时不再标记
      if (graphInstance === graph) {
        isGraphRendered = true;
      }
    });
  };

  /**
   * 容器尺寸变化（全屏切换、窗口缩放）时同步画布尺寸并重新居中，保留当前缩放
   */
  const resizeGraph = () => {
    if (!graphInstance || !isGraphRendered) {
      return;
    }
    graphInstance.resize();
    graphInstance.fitCenter(false);
  };

  /**
   * 还原到初始视图：缩放 1 倍并居中（与初始化的 autoFit: 'center' 一致）
   * fitView / zoomTo 都是异步动画，并发调用会互相打断，需先完成缩放再居中
   */
  const handleZoomReset = async () => {
    if (!graphInstance) {
      return;
    }
    await graphInstance.zoomTo(1, false);
    await graphInstance.fitCenter();
  };

  /**
   * 放大：按倍率缩放，各缩放级别下每步观感一致
   */
  const handleZoomIn = () => {
    const currentZoom = graphInstance?.getZoom();
    if (currentZoom) {
      graphInstance!.zoomTo(currentZoom * 1.1);
    }
  };

  /**
   * 缩小
   */
  const handleZoomOut = () => {
    const currentZoom = graphInstance?.getZoom();
    if (currentZoom) {
      graphInstance!.zoomTo(currentZoom / 1.1);
    }
  };

  /**
   * 获取实例详情
   */
  const fetchInstDetails = (nodeData: TopoNodeData) => {
    const address = nodeData.node_id;
    const getApi = () => {
      if (isK8sCluster.value) {
        return k8sApiMap[props.clusterType as keyof typeof k8sApiMap]({
          cluster_id: props.clusterData.id,
          clusterName: props.clusterData.cluster_name,
          // Pod 节点的 node_type 即组件名
          componentName: nodeData.node_type,
          k8sClusterName: props.clusterData.k8s_cluster_name!,
          namespace: props.clusterData.namespace!,
          podName: address,
        });
      }

      return apiMap[props.clusterType as keyof typeof apiMap]({
        cluster_id: props.clusterData.id,
        dbType: props.dbType,
        instance: address,
        type: props.clusterType,
      });
    };

    instState.loadingIds.add(address);
    return getApi()
      .then((details) => {
        instState.detailsCaches.set(address, details);
      })
      .finally(() => {
        instState.loadingIds.delete(address);
      });
  };

  /**
   * 销毁图实例与节点详情浮层
   */
  const destroyGraph = () => {
    hideTips();
    isGraphRendered = false;
    graphInstance?.destroy();
    graphInstance = null;
  };

  return {
    destroyGraph,
    fetchInstDetails,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
    instDetails,
    instState,
    isInstLoading,
    renderDraph,
    resizeGraph,
  };
};
