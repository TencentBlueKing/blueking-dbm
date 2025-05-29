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

import _ from 'lodash';
import type { Instance } from 'tippy.js';
import type { VNode } from 'vue';
import type { JSX } from 'vue/jsx-runtime';

import D3Graph from '@blueking/bkflow.js';

import { retrieveDorisInstance } from '@services/source/doris';
import { retrieveEsInstance } from '@services/source/es';
import { retrieveHdfsInstance } from '@services/source/hdfs';
import { retrieveKafkaInstance } from '@services/source/kafka';
import { retrieveMongoInstanceDetail } from '@services/source/mongodb';
import { retrievePulsarInstance } from '@services/source/pulsar';
import { retrieveRedisInstance } from '@services/source/redis';
import { retrieveRiakInstance } from '@services/source/riak';
import { getTendbclusterInstanceDetail } from '@services/source/tendbcluster';
import { retrieveTendbhaInstance } from '@services/source/tendbha';
import { retrieveTendbsingleInstance } from '@services/source/tendbsingle';
import type { ResourceTopo } from '@services/types';

import { useGlobalBizs } from '@stores';

import { DBTypes } from '@common/const';
import { dbTippy } from '@common/tippy';

import DbStatus from '@components/db-status/index.vue';

import { generateId, vNodeToHtml } from '@utils';

import { t } from '@locales/index';

import { checkOverflow } from '@/directives/overflowTips';

import {
  type GraphInstance,
  type GraphLine,
  type GraphNode,
  GroupTypes,
  type NodeConfig,
  nodeTypes,
} from './graphData';

interface InstanceDetails {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_cpu: number;
  bk_disk: number;
  bk_host_id: number;
  bk_host_innerip: string;
  bk_idc_city_name: string;
  bk_idc_name: string;
  bk_mem: number;
  bk_os_name: string;
  bk_sub_zone: string;
  cluster_id: number;
  cluster_type: string;
  cluster_type_display: string;
  create_at: string;
  db_module_id: number;
  db_version: string;
  idc_city_id: string;
  idc_city_name: string;
  idc_id: number;
  instance_address: string;
  master_domain: string;
  net_device_id: string;
  rack: string;
  rack_id: number;
  role: string;
  slave_domain: string;
  status: string;
  sub_zone: string;
  version?: string;
}

interface ClusterTopoProps {
  clusterType: string;
  dbType: string;
  id: number;
}

type ResourceTopoNode = ResourceTopo['nodes'][number];
type DetailColumnsRenderFunc<T> = (value: T) => JSX.Element;

type DetailColumns<T> = {
  key: keyof InstanceDetails;
  label: string;
  render?: DetailColumnsRenderFunc<T>;
}[];

// 实例信息
export const detailColumns: DetailColumns<any> = [
  {
    key: 'role',
    label: t('部署角色'),
  },
  {
    key: 'db_version',
    label: t('版本'),
  },
  {
    key: 'status',
    label: t('状态'),
    render: (status: 'running' | 'unavailable') => {
      if (!status) {
        return <span>--</span>;
      }

      const statusMap = {
        running: {
          text: t('运行中'),
          theme: 'success',
        },
        unavailable: {
          text: t('异常'),
          theme: 'danger',
        },
      };
      const info = statusMap[status] || statusMap.unavailable;
      return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
    },
  },
  {
    key: 'bk_host_innerip',
    label: t('主机IP'),
  },
  {
    key: 'bk_idc_city_name',
    label: t('地域'),
  },
  {
    key: 'bk_sub_zone',
    label: t('园区'),
  },
  {
    key: 'bk_cpu',
    label: 'CPU',
    render: (value: number) => <span>{Number.isFinite(value) ? `${value}${t('核')}` : '--'}</span>,
  },
  {
    key: 'bk_mem',
    label: t('内存'),
    render: (value: number) => <span>{Number.isFinite(value) ? `${value}MB` : '--'}</span>,
  },
  {
    key: 'bk_disk',
    label: t('硬盘'),
    render: (value: number) => <span>{Number.isFinite(value) ? `${value}GB` : '--'}</span>,
  },
];

const apiMap: Record<string, (params: any) => Promise<any>> = {
  doris: retrieveDorisInstance,
  es: retrieveEsInstance,
  hdfs: retrieveHdfsInstance,
  kafka: retrieveKafkaInstance,
  mongodb: retrieveMongoInstanceDetail,
  pulsar: retrievePulsarInstance,
  redis: retrieveRedisInstance,
  riak: retrieveRiakInstance,
  tendbcluster: getTendbclusterInstanceDetail,
  tendbha: retrieveTendbhaInstance,
  tendbsingle: retrieveTendbsingleInstance,
};

const entryTagMap: Record<string, string> = {
  entry_clb: 'CLB',
  entry_polaris: t('北极星'),
};

export const useRenderGraph = (props: ClusterTopoProps, nodeConfig: NodeConfig = {}) => {
  const graphState = reactive({
    instance: null as any,
    isLoadNodeDetatils: false,
    topoId: generateId('cluster_topo_'),
  });
  const tippyInstances: Map<string, Instance> = new Map();

  function renderDraph(locations: GraphNode[], lines: GraphLine[]) {
    if (graphState.instance) {
      graphState.instance.destroy(true);
    }

    graphState.instance = new D3Graph(`#${graphState.topoId}`, {
      background: '#F5F7FA',
      canvasPadding: { x: 200, y: 0 },
      lineConfig: {
        activeColor: '#C4C6CC',
        canvasLine: false,
        color: '#C4C6CC',
      },
      mode: 'readonly',
      nodeConfig: _.cloneDeep(locations),
      nodeTemplateKey: 'id',
      onNodeRender: getNodeRender,
      zoom: {
        controlPanel: false,
        scaleExtent: [0.5, 1.5],
      },
    })
      .on('nodeMouseEnter', async (node: GraphNode, e: MouseEvent) => {
        if (node.type === GroupTypes.GROUP) {
          return;
        }

        // 设置激活节点 z-index

        // 设置激活节点 z-index
        if (e.target) {
          (e.target as HTMLElement).style.zIndex = '1';
        }

        const el = document.getElementById(node.id);
        // entry 所属节点若超出则显示tips
        if (node.belong.includes('entry')) {
          const contentEl = el?.querySelector('.cluster-node__content');
          if (el && contentEl && checkOverflow(contentEl)) {
            const instance = dbTippy(el, {
              content: node.id,
              offset: [0, 5],
              placement: 'right',
              theme: 'light',
            });
            tippyInstances.set(node.id, instance);
          }
          return;
        }

        // 获取 tips 内容
        const template = document.getElementById('node-details-tips');
        const content = template?.querySelector?.('.node-details');
        if (el && content) {
          // 获取详情数据
          if (!instState.detailsCaches.get(node.id)) {
            fetchInstDetails(node.id);
          }
          // 设置节点详情
          nextTick(() => {
            const instance = dbTippy(el, {
              allowHTML: true,
              appendTo: () => el,
              arrow: true,
              content,
              hideOnClick: false,
              interactive: true,
              maxWidth: 320,
              offset: [0, 5],
              onHidden: () => template?.append?.(content),
              placement: 'right-start',
              // trigger: 'manual',
              theme: 'light',
              zIndex: 9999,
            });
            tippyInstances.set(node.id, instance);
            instState.activeId = node.id;
            instState.nodeData = node.data as ResourceTopoNode;
          });
        }
      })
      .on('nodeMouseLeave', (node: GraphNode, e: MouseEvent) => {
        if (node.type === GroupTypes.GROUP) {
          return;
        }

        const tippy = tippyInstances.get(node.id);
        tippy?.destroy();
        tippyInstances.delete(node.id);

        // 设置激活节点 z-index
        if (e.target) {
          (e.target as HTMLElement).style.zIndex = '';
        }
        instState.nodeData = null;
      });
    graphState.instance.renderGraph({ lines, locations }, false);
    renderLineLabels(graphState.instance, lines, locations, nodeConfig);
  }

  /**
   * 还原缩放
   */
  function handleZoomReset() {
    graphState.instance?.reSet();
  }

  /**
   * 缩小
   */
  function handleZoomIn() {
    graphState.instance?.zoomIn();
  }

  /**
   * 放大
   */
  function handleZoomOut() {
    graphState.instance?.zoomOut();
  }

  const globalBizsStore = useGlobalBizs();
  const instState = reactive<{
    activeId: string;
    detailsCaches: Map<string, InstanceDetails>;
    isLoading: boolean;
    nodeData: ResourceTopoNode | null;
  }>({
    activeId: '',
    detailsCaches: new Map(),
    isLoading: false,
    nodeData: null,
  });
  const instDetails = computed(() => instState.detailsCaches.get(instState.activeId));
  /**
   * 获取实例详情
   */
  function fetchInstDetails(address: string) {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.id,
      dbType: props.dbType,
      instance_address: address,
      type: props.clusterType,
    };
    instState.isLoading = true;
    return apiMap[props.clusterType](params)
      .then((res) => {
        instState.detailsCaches.set(address, res);
      })
      .finally(() => {
        instState.isLoading = false;
      });
  }

  /**
   * 获取渲染节点 html
   * @param node 渲染节点
   * @returns 节点 html
   */
  function getNodeRender(node: GraphNode) {
    let vNode: VNode | string = '';

    if (props.dbType === DBTypes.RIAK) {
      const { status, url } = node.data as ResourceTopoNode;
      vNode = (
        <div
          id={node.id}
          class={['cluster-node', 'riak-node', { 'has-link': url }]}>
          <svg class='db-svg-icon'>
            <use xlinkHref={`#db-icon-${status === 'running' ? 'sync-success' : 'sync-failed'}`} />
          </svg>
          <div class='cluster-node__content riak-node-content text-overflow ml-4'>{node.id}</div>
        </div>
      );
    } else {
      const isInstance = [nodeTypes.MASTER, nodeTypes.SLAVE].includes(node.id);
      const iconType = isInstance ? 'cluster-group__icon--round' : '';
      const isGroup = node.type === GroupTypes.GROUP;

      if (isGroup) {
        vNode = (
          <div class='cluster-group'>
            <div class='cluster-group__title'>
              <span class={['cluster-group__icon', iconType]}>{node.label.charAt(0).toUpperCase()}</span>
              <h5 class='cluster-group__label'>{node.label}</h5>
            </div>
          </div>
        );
      } else {
        const { node_type: nodeType, url } = node.data as ResourceTopoNode;
        const isEntryExternalLinks = nodeType.startsWith('entry_') && /^https?:\/\//.test(url);
        vNode = (
          <div
            id={node.id}
            class={['cluster-node', { 'has-link': url }]}>
            {isEntryExternalLinks ? (
              <a
                href={url}
                style='display: flex; align-items: center; color: #63656E;'
                target='__blank'>
                <span class='cluster-node__content text-overflow'>{node.id}</span>
                {entryTagMap[nodeType] ? <span class='cluster-node__tag'>{entryTagMap[nodeType]}</span> : null}
                <i
                  class='db-icon-link cluster-node__link'
                  style='flex-shrink: 0; color: #3a84ff;'
                />
              </a>
            ) : (
              <div class='cluster-node__content text-overflow'>{node.id}</div>
            )}
          </div>
        );
      }
    }

    const html = vNodeToHtml(vNode);
    return typeof html === 'string' ? html : html.outerHTML;
  }

  return {
    graphState,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
    instDetails,
    instState,
    renderDraph,
  };
};

/**
 * 绘制连线 label
 * @param graphInstance flow 实例
 * @param lines 连线列表
 * @param nodes 节点列表
 */
function renderLineLabels(
  graphInstance: GraphInstance,
  lines: GraphLine[],
  nodes: GraphNode[],
  nodeConfig: NodeConfig = {},
) {
  if (graphInstance?._diagramInstance?._canvas) {
    // eslint-disable-next-line no-underscore-dangle
    graphInstance._diagramInstance._canvas
      .insert('div', ':first-child')
      .attr('class', 'db-graph-labels')
      .selectAll('span')
      .data(lines)
      .enter()
      .append('span')
      .attr('class', 'db-graph-label')
      .text((line: GraphLine) => line.label)
      .style('position', 'absolute')
      .style('left', (line: GraphLine) => {
        const { source, target } = line;
        const sourceNode = nodes.find((node) => node.id === source.id);
        const targetNode = nodes.find((node) => node.id === target.id);
        const sWidth = sourceNode ? sourceNode.width : 0;
        const sourceEndX = source.x + sWidth / 2;
        const tWidth = targetNode ? targetNode.width : 0;
        const targetStartX = target.x - tWidth / 2;
        const x = source.x === target.x ? target.x : sourceEndX + (targetStartX - sourceEndX) / 2;
        return `${x}px`;
      })
      .style('top', (line: GraphLine) => {
        const { source, target } = line;
        const sourceNode = nodes.find((node) => node.id === source.id);
        const targetNode = nodes.find((node) => node.id === target.id);
        const sHeight = sourceNode ? sourceNode.height : 0;
        const sourceEndY = source.y + sHeight / 2;
        const tHeight = targetNode ? targetNode.height : 0;
        const targetStartY = target.y - tHeight / 2;
        const y = source.y === target.y ? target.y : sourceEndY + (targetStartY - sourceEndY) / 2;
        return `${y}px`;
      })
      .style('transform', 'translate(-50%, -50%)');
  }
}
