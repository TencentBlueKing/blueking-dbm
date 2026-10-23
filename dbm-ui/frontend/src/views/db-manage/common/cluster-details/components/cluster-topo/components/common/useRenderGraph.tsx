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
import type { ResourceTopo } from '@services/types';

import { ClusterTypes } from '@common/const';
import { ipPort } from '@common/regex';
import { dbTippy } from '@common/tippy';

import { getExclusiveClusterParams } from '@views/db-manage/utils/exclusiveClusterParams';

import { ExtensionCategory, Graph, type GraphData as GraphDataG6, type NodeData, NodeEvent, register } from '@antv/g6';

import { GraphData, GroupTypes, type NodeConfig } from './graphData';
import { TopoNode } from './topoNode';

const apiMap = {
  [ClusterTypes.DORIS]: retrieveDorisInstance,
  [ClusterTypes.ES]: retrieveEsInstance,
  [ClusterTypes.HDFS]: retrieveHdfsInstance,
  [ClusterTypes.KAFKA]: retrieveKafkaInstance,
  [ClusterTypes.MONGO_REPLICA_SET]: retrieveMongoInstanceDetail,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: retrieveMongoInstanceDetail,
  // [ClusterTypes.REDIS_CLUSTER]: retrieveRedisInstance,
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: retrieveRedisInstance,
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: retrieveRedisInstance,
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
};

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
  clusterType: keyof typeof apiMap | keyof typeof k8sApiMap;
  dbType: string;
  nodeConfig?: NodeConfig;
}

register(ExtensionCategory.NODE, 'topo-node', TopoNode);

export const useRenderGraph = (props: ClusterTopoProps) => {
  let graphInstance: Graph | null = null;
  let tippyInstance: Instance | undefined;

  const instState = reactive<{
    activeId: string;
    detailsCaches: Map<string, any>;
    isLoading: boolean;
    nodeData: ResourceTopo['nodes'][number] | null;
  }>({
    activeId: '',
    detailsCaches: new Map(),
    isLoading: false,
    nodeData: null,
  });

  const instDetails = computed(() => instState.detailsCaches.get(instState.activeId));

  watch(
    () => instState.activeId,
    () => {
      if (instState.activeId) {
        if (instState.detailsCaches.get(instState.activeId)) {
          return;
        }

        fetchInstDetails(instState.activeId);
      }
    },
  );

  const renderDraph = (data: ResourceTopo) => {
    if (props.clusterData.isOffline) {
      return;
    }
    graphInstance?.destroy();
    const graphData = new GraphData(props.clusterType, props.nodeConfig).formatGraphData(data, props.dbType);
    graphInstance = new Graph({
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
        type: 'cubic-horizontal',
      },
      node: {
        style: {
          fill: '#fff',
          // 实例行节点叠放在分组节点内，上下边被相邻行和分组遮住，
          // 不配端口时连线按中心方向取矩形交点，斜线会落到上下边导致箭头被盖住，
          // 因此只开放左右两侧端口（简单端口不绘制图形），分组节点保持默认交点
          ports: (d: NodeData) =>
            (d as unknown as { type: GroupTypes }).type === GroupTypes.NODE
              ? [
                  { key: 'left', placement: 'left' },
                  { key: 'right', placement: 'right' },
                ]
              : [],
          radius: 4,
          shadowColor: '#1919290d',
          shadowOffsetX: 2,
          shadowOffsetY: 4,
          size: (d: NodeData) => [d.style!.width as number, d.style!.height as number],
        },
        type: 'topo-node',
      },
    });
    graphInstance.on(NodeEvent.POINTER_ENTER, (e: any) => {
      const { height, width, x, y } = e.target.data.style;
      const targetId = e.target.id;
      if (!ipPort.test(targetId)) {
        return;
      }

      const template = document.getElementById('node-details-tips');
      const content = template?.querySelector('.node-details');
      if (content) {
        // 以节点完整矩形为参照，左侧空间不足翻转到右侧时贴着节点右边缘，不会盖住节点
        const [left, top] = graphInstance!.getClientByCanvas([x - width / 2, y - height / 2]);
        const [right, bottom] = graphInstance!.getClientByCanvas([x + width / 2, y + height / 2]);
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
        // 上一个浮层未正常离开时先销毁，避免残留
        tippyInstance?.destroy();
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
          hideOnClick: false,
          interactive: true,
          maxWidth: 320,
          onDestroy: () => resizeObserver.disconnect(),
          onHidden: () => template?.append?.(content!),
          placement: 'left-start',
          theme: 'light',
          zIndex: 9999,
        });
        tippy.setProps({
          getReferenceClientRect: () => referenceRect as DOMRect,
        });
        tippy.show();
        tippyInstance = tippy;
        resizeObserver.observe(content);
        instState.activeId = targetId;
        instState.nodeData = e.target.data;
      }
    });

    graphInstance.on(NodeEvent.POINTER_LEAVE, (e: any) => {
      const targetId = e.target.id;
      if (!ipPort.test(targetId)) {
        return;
      }

      tippyInstance?.destroy();
    });
    graphInstance.render();
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
   * 放大
   */
  const handleZoomIn = () => {
    const currentZoom = graphInstance?.getZoom();
    if (currentZoom) {
      graphInstance!.zoomTo(currentZoom + 0.1);
    }
  };

  /**
   * 缩小
   */
  const handleZoomOut = () => {
    const currentZoom = graphInstance?.getZoom();
    if (currentZoom) {
      graphInstance!.zoomTo(currentZoom - 0.1);
    }
  };

  /**
   * 获取实例详情
   */
  const fetchInstDetails = (address: string) => {
    const getApi = () => {
      if (props.clusterType in k8sApiMap) {
        return k8sApiMap[props.clusterType as keyof typeof k8sApiMap]({
          cluster_id: props.clusterData.id,
          clusterName: props.clusterData.cluster_name,
          componentName: '',
          k8sClusterName: props.clusterData.k8s_cluster_name!,
          namespace: props.clusterData.namespace!,
          podName: address,
          ...getExclusiveClusterParams(props.clusterData),
        });
      }

      return apiMap[props.clusterType as keyof typeof apiMap]({
        cluster_id: props.clusterData.id,
        dbType: props.dbType,
        instance: address,
        type: props.clusterType,
      });
    };

    instState.isLoading = true;
    return getApi()
      .then((details) => {
        instState.detailsCaches.set(address, details);
      })
      .finally(() => {
        instState.isLoading = false;
      });
  };

  /**
   * 销毁图实例与节点详情浮层
   */
  const destroyGraph = () => {
    tippyInstance?.destroy();
    tippyInstance = undefined;
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
    renderDraph,
  };
};
