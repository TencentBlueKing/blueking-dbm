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
import { retrieveRedisInstance } from '@services/source/redis';
import { retrieveRiakInstance } from '@services/source/riak';
import { retrieveSqlserverHaInstance } from '@services/source/sqlserveHaCluster';
import { retrieveSqlserverSingleInstance } from '@services/source/sqlserverSingleCluster';
import { getTendbclusterInstanceDetail } from '@services/source/tendbcluster';
import { retrieveTendbhaInstance } from '@services/source/tendbha';
import { retrieveTendbsingleInstance } from '@services/source/tendbsingle';
import type { ResourceTopo } from '@services/types';

import { ClusterTypes } from '@common/const';
import { ipPort } from '@common/regex';
import { dbTippy } from '@common/tippy';

import { ExtensionCategory, Graph, type GraphData as GraphDataG6, type NodeData, NodeEvent, register } from '@antv/g6';

import { GraphData, type NodeConfig } from './graphData';
import { TopoNode } from './topoNode';

const apiMap = {
  [ClusterTypes.DORIS]: retrieveDorisInstance,
  [ClusterTypes.ES]: retrieveEsInstance,
  [ClusterTypes.HDFS]: retrieveHdfsInstance,
  [ClusterTypes.KAFKA]: retrieveKafkaInstance,
  [ClusterTypes.MONGO_REPLICA_SET]: retrieveMongoInstanceDetail,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: retrieveMongoInstanceDetail,
  [ClusterTypes.PULSAR]: retrievePulsarInstance,
  [ClusterTypes.REDIS_CLUSTER]: retrieveRedisInstance,
  [ClusterTypes.REDIS_INSTANCE]: retrieveRedisInstance,
  [ClusterTypes.RIAK]: retrieveRiakInstance,
  [ClusterTypes.SQLSERVER_HA]: retrieveSqlserverHaInstance,
  [ClusterTypes.SQLSERVER_SINGLE]: retrieveSqlserverSingleInstance,
  [ClusterTypes.TENDBCLUSTER]: getTendbclusterInstanceDetail,
  [ClusterTypes.TENDBHA]: retrieveTendbhaInstance,
  [ClusterTypes.TENDBSINGLE]: retrieveTendbsingleInstance,
};

interface ClusterTopoProps {
  clusterType: keyof typeof apiMap;
  dbType: string;
  id: number;
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
    graphInstance?.destroy();
    const graphData = new GraphData(props.clusterType, props.nodeConfig).formatGraphData(data, props.dbType);
    graphInstance = new Graph({
      animation: true,
      autoFit: 'center',
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
        const [targetX, targetY] = graphInstance!.getClientByCanvas([x - width / 2, y - height / 3]);
        const tippy = dbTippy(document.body, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: true,
          content,
          hideOnClick: false,
          interactive: true,
          maxWidth: 320,
          onHidden: () => template?.append?.(content!),
          placement: 'left-start',
          theme: 'light',
          zIndex: 9999,
        });
        tippy.setProps({
          getReferenceClientRect: () =>
            ({
              bottom: targetY,
              height: 0,
              left: targetX,
              right: targetX,
              top: targetY,
              width: 0,
              x,
              y,
            }) as any,
        });
        tippy.show();
        tippyInstance = tippy;
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
   * 还原缩放
   */
  const handleZoomReset = () => {
    graphInstance?.fitView();
    graphInstance?.zoomTo(1);
  };

  /**
   * 缩小
   */
  const handleZoomIn = () => {
    const currentZoom = graphInstance?.getZoom();
    if (currentZoom) {
      graphInstance!.zoomTo(currentZoom + 0.1);
    }
  };

  /**
   * 放大
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
    const params = {
      cluster_id: props.id,
      dbType: props.dbType,
      instance: address,
      type: props.clusterType,
    };
    instState.isLoading = true;
    return apiMap[props.clusterType](params)
      .then((details) => {
        instState.detailsCaches.set(address, details);
      })
      .finally(() => {
        instState.isLoading = false;
      });
  };

  return {
    fetchInstDetails,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
    instDetails,
    instState,
    renderDraph,
  };
};
