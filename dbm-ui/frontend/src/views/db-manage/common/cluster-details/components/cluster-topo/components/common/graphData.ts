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

import type { ResourceTopo } from '@services/types';

import { ClusterTypes, DBTypes } from '@common/const';

export type NodeConfig = Partial<typeof defaultNodeConfig>;

/** 节点内文案的左边距、右边距（topoNode 绘制文案与这里计算行高共用） */
export const TEXT_LEFT_OFFSET = 46;
export const TEXT_RIGHT_PADDING = 12;
/** 文案行高，与 @antv/g Text 默认值（fontSize + lineWidth）一致 */
export const TEXT_LINE_HEIGHT = 13;
/** 单行文案最多折成几行，超出走省略号 */
export const TEXT_MAX_LINES = 2;

/** 复用 canvas 测量文案宽度 */
let measureCtx: CanvasRenderingContext2D | null = null;
const measureTextWidth = (text: string, font = '12px Arial') => {
  if (!measureCtx) {
    measureCtx = document.createElement('canvas').getContext('2d')!;
  }
  measureCtx.font = font;
  return measureCtx.measureText(text).width;
};

/**
 * 估算文案在给定宽度下的折行行数，与 @antv/g 的 wordWrap 行为对齐：
 * 优先按空格断行，单个超长片段按字符断行
 */
const getWrapLineCount = (text: string, availableWidth: number) => {
  if (availableWidth <= 0) {
    return 1;
  }

  let lines = 1;
  let lineWidth = 0;
  for (const word of text.split(' ')) {
    const wordWidth = measureTextWidth(word);
    const spaceWidth = lineWidth > 0 ? measureTextWidth(' ') : 0;
    if (lineWidth > 0 && lineWidth + spaceWidth + wordWidth > availableWidth) {
      lines += 1;
      lineWidth = wordWidth;
    } else {
      lineWidth += spaceWidth + wordWidth;
    }
    // 单个片段超过整行宽度时按字符折行
    while (lineWidth > availableWidth) {
      lines += 1;
      lineWidth -= availableWidth;
    }
  }

  return Math.min(lines, TEXT_MAX_LINES);
};

/** 拓扑图节点文案：ip:port + 可展示的 Mongo instance_state（隐藏 NOT_INITIALIZED/SECONDARY） */
const HIDDEN_INSTANCE_STATES = new Set(['NOT_INITIALIZED', 'SECONDARY']);

const formatTopoNodeName = (node: ResourceTopo['nodes'][number]) => {
  const state = node.instance_state;
  if (!state || HIDDEN_INSTANCE_STATES.has(state)) {
    return node.node_id;
  }
  return `${node.node_id} ${state}`;
};

// 节点连线结构
export interface GraphLine {
  id: string;
  isSameY: boolean;
  label: string;
  source: string;
  style?: {
    sourcePort: string;
    targetPort: string;
  };
  target: string;
  /** 分组间连线按相对位置选横向或纵向曲线，未指定时用默认 cubic-horizontal */
  type?: 'cubic-horizontal' | 'cubic-vertical';
}

// graph node types
export enum GroupTypes {
  GROUP = 'group',
  NODE = 'node',
}

// 节点返回数据结构
export interface GraphNode {
  belong: string; // 节点所属组 ID
  children: GraphNode[];
  data: ResourceTopo['nodes'][number] | ResourceTopo['groups'][number];
  id: string;
  name: string;
  style: {
    height: number;
    width: number;
    x: number;
    y: number;
  };
  type: GroupTypesStrings; // 节点类型 group | node
}

export interface GraphInstance {
  _diagramInstance?: {
    _canvas?: any;
  };
}

// 节点类型
export const nodeTypes = {
  CLB_DNS_ENTRY_GROUP: 'clb_dns_entry_group',
  CLB_ENTRY_GROUP: 'clb_entry_group',
  CLB_MASTER_DNS_ENTRY_GROUP: 'clb_master_dns_entry_group',
  CLB_MASTER_ENTRY_GROUP: 'clb_master_entry_group',
  CLB_SLAVE_DNS_ENTRY_GROUP: 'clb_slave_dns_entry_group',
  CLB_SLAVE_ENTRY_GROUP: 'clb_slave_entry_group',
  DNS_ENTRY_GROUP: 'dns_entry_group',
  DNS_MASTER_ENTRY_GROUP: 'dns_master_entry_group',
  DNS_SLAVE_ENTRY_GROUP: 'dns_slave_entry_group',
  ENTRY_DNS: 'entry_dns',
  ES_DATANODE_COLD: 'es_datanode::es_datanode_cold',
  ES_DATANODE_HOT: 'es_datanode::es_datanode_hot',
  ES_MASTER: 'es_master::es_master',
  HDFS_DATANODE: 'hdfs_datanode::hdfs_datanode',
  HDFS_MASTER_HOURNALNODE: 'hdfs_master::hdfs_journalnode',
  HDFS_MASTER_NAMENODE: 'hdfs_master::hdfs_namenode',
  HDFS_MASTER_ZOOKEEPER: 'hdfs_master::hdfs_zookeeper',
  MASTER: 'backend::backend_master',
  MASTER_ENTRY_GROUP: 'master_entry_group',
  MONGODB_BACKUP: 'mongodb::backup',
  MONGODB_CONFIG: 'mongo_config::m1',
  MONGODB_M1: 'mongodb::m1',
  MONGODB_M2: 'mongodb::m2',
  MONGODB_MONGOS: 'mongos',
  /** 分片集群拓扑：合并后的「共 N 分片」组（与后端 MONGODB_SHARDS_GROUP_ID 对齐） */
  MONGODB_SHARDS: 'mongodb_shards',
  ORACLE_PRIMARY: 'oracle::primary',
  ORACLE_STANDBY: 'oracle::standby',
  PD: 'pd',
  PROXY: 'proxy',
  PULSAR_BOOKKEEPER: 'pulsar_bookkeeper::pulsar_bookkeeper',
  PULSAR_BROKER: 'pulsar_broker::pulsar_broker',
  PULSAR_ZOOKEEPER: 'pulsar_zookeeper::pulsar_zookeeper',
  SLAVE: 'backend::backend_slave',
  SPIDER_MASTER_ENTRY_BIND: 'spider_master_entry_bind',
  SPIDER_SLAVE_ENTRY_BIND: 'spider_slave_entry_bind',
  SURREAL: 'surreal',
  TENDBCLUSTER_CONTROLLER: 'controller_group',
  TENDBCLUSTER_MASTER: 'spider_master',
  TENDBCLUSTER_MNT: 'spider_mnt',
  TENDBCLUSTER_REMOTE_MASTER: 'remote::remote_master',
  TENDBCLUSTER_REMOTE_SLAVE: 'remote::remote_slave',
  TENDBCLUSTER_SLAVE: 'spider_slave',
  TENDISCACHE_MASTER: 'tendiscache::redis_master',
  TENDISCACHE_SLAVE: 'tendiscache::redis_slave',
  TENDISPLUS_MASTER: 'tendisplus::redis_master',
  TENDISPLUS_SLAVE: 'tendisplus::redis_slave',
  TENDISSSD_MASTER: 'tendisssd::redis_master',
  TENDISSSD_SLAVE: 'tendisssd::redis_slave',
  TIKV: 'tikv',
  VMINSERT: 'vminsert',
  VMSELECT: 'vmselect',
};

type GroupTypesStrings = `${GroupTypes}`;

const defaultNodeConfig = {
  groupTitle: 44,
  itemHeight: 28,
  minHeight: 54,
  /** 节点最小宽度，文案很短时也保持卡片观感 */
  minWidth: 200,
  /** Mongo「共 N 分片」行文案较长：shard / ip:port,...，作为该组的最大宽度 */
  mongoShardsWidth: 560,
  /** 节点水平间距，需留出连线标签宽度（如「访问」「绑定」） */
  offsetX: 100,
  /** 节点垂直间距，需留出连线标签高度与箭头 */
  offsetY: 48,
  startX: 100,
  startY: 100,
  /** 节点最大宽度，实际宽度按整张图最长文案自适应，超出时折行 */
  width: 296,
};

/** 分组标题字体，与 topoNode 绘制分组标题一致 */
const GROUP_TITLE_FONT = '700 12px Arial';

// 需要水平排列特定分组的集群类型（es / hdfs / mongo）
const HORIZONTAL_ALIGN_CLUSTER_TYPES: string[] = [
  ClusterTypes.ES,
  ClusterTypes.HDFS,
  ClusterTypes.MONGO_REPLICA_SET,
  ClusterTypes.MONGO_SHARED_CLUSTER,
];

// 有专属布局函数的集群类型，通用布局阶段不做重叠避让
const CUSTOM_LAYOUT_CLUSTER_TYPES: string[] = [
  ...HORIZONTAL_ALIGN_CLUSTER_TYPES,
  ClusterTypes.TENDBCLUSTER,
  ClusterTypes.TENDBHA,
  ClusterTypes.K8S_SURREALDB_HA,
  ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER,
];

// 特殊逻辑：控制节点水平对齐
const sameSources = [
  nodeTypes.MASTER,
  nodeTypes.TENDISCACHE_MASTER,
  nodeTypes.TENDISPLUS_MASTER,
  nodeTypes.TENDISSSD_MASTER,
  nodeTypes.PULSAR_BROKER,
  nodeTypes.TENDBCLUSTER_REMOTE_MASTER,
  nodeTypes.TENDBCLUSTER_MASTER,
  nodeTypes.MONGODB_M1,
  nodeTypes.MONGODB_MONGOS,
  nodeTypes.ORACLE_PRIMARY,
];
const sameTargets = [
  nodeTypes.SLAVE,
  nodeTypes.TENDISCACHE_SLAVE,
  nodeTypes.TENDISPLUS_SLAVE,
  nodeTypes.TENDISSSD_SLAVE,
  nodeTypes.PULSAR_ZOOKEEPER,
  nodeTypes.TENDBCLUSTER_REMOTE_SLAVE,
  nodeTypes.TENDBCLUSTER_SLAVE,
  nodeTypes.MONGODB_M2,
  nodeTypes.MONGODB_CONFIG,
  nodeTypes.ORACLE_STANDBY,
];

/**
 * 获取 group 间连线
 */
const getGroupLines = (data: ResourceTopo) => {
  const { groups, lines } = data;
  const results: GraphLine[] = [];

  for (const line of lines) {
    const { label_name: labelName, source, source_type: sourceType, target, target_type: targetType } = line;
    let sourceId = source;
    let targetId = target;

    // 如果 source 和 taget 均为 node 类型
    if (sourceType === 'node' && targetType === 'node') {
      for (const group of groups) {
        if (group.children_id.includes(source)) {
          sourceId = group.node_id;
          continue;
        }
        if (group.children_id.includes(target)) {
          targetId = group.node_id;
          continue;
        }
      }
    } else if (sourceType === 'node') {
      // 处理 source 为 node 的情况
      const sourceGroup = groups.find((group) => group.children_id.includes(source));
      if (sourceGroup) {
        sourceId = sourceGroup.node_id;
      }
    } else if (targetType === 'node') {
      // 处理 target 为 node 的情况
      const targetGroup = groups.find((group) => group.children_id.includes(target));
      if (targetGroup) {
        targetId = targetGroup.node_id;
      }
    }
    results.push({
      id: `${sourceId}__${targetId}`,
      // source 为 master 且 target 为 slave 则 y 值相等
      isSameY: sameSources.includes(sourceId) && sameTargets.includes(targetId), // TODO: 这里是节点并列特殊逻辑
      label: labelName,
      source: sourceId,
      target: targetId,
    });
  }
  return results;
};

/**
 * 获取实际画图连线
 */
const getLines = (data: ResourceTopo) => {
  const { lines } = data;
  const results = [];

  for (const line of lines) {
    const { label_name: labelName, source, target } = line;
    const sourceId = source;
    const targetId = target;

    results.push({
      id: `${sourceId}__${targetId}`,
      // source为master且target为slave 则 y 值相等
      isSameY: sameSources.includes(sourceId) && sameTargets.includes(targetId), // TODO: 这里是节点并列特殊逻辑
      label: labelName,
      source: sourceId,
      target: targetId,
    });
  }
  return _.uniqBy(results, 'id');
};

export class GraphData {
  clusterType: string;
  graphData: {
    edges: GraphLine[];
    nodes: GraphNode[];
  } = { edges: [], nodes: [] };

  mongoShardsNodeWidth = defaultNodeConfig.mongoShardsWidth;

  nodeConfig: typeof defaultNodeConfig = { ...defaultNodeConfig };
  /** 本图统一节点宽度、Mongo 分片组宽度，由 calcNodeWidths 计算 */
  nodeWidth = defaultNodeConfig.width;

  constructor(clusterType: string, nodeConfig: NodeConfig = {}) {
    this.nodeConfig = Object.assign(this.nodeConfig, nodeConfig);
    this.clusterType = clusterType;
  }

  /**
   * 设置 children locations
   */
  calcChildrenNodeLocations(targetNode: GraphNode) {
    const { groupTitle } = this.nodeConfig;
    // 坐标为节点中心点，行高可能因折行不同，需按「上边缘 + 半高」逐行累加，不能直接加上一行高度
    let rowTop = targetNode.style.y - targetNode.style.height / 2 + groupTitle;
    for (const childNode of targetNode.children) {
      childNode.style.x = targetNode.style.x;
      childNode.style.y = rowTop + childNode.style.height / 2;
      rowTop += childNode.style.height;
    }
  }

  /**
   * 计算分组间连线的端口：连线固定落在分组某条边的中点，曲线方向与端口方向一致，
   * 避免按中心方向取交点时落到边角、箭头沿边框横躺被节点盖住
   * 实例行之间的连线保持原逻辑（实例行只有左右端口，由 G6 就近选择）
   * @param edges 连线列表
   * @param nodes 已定位的节点列表
   */
  calcEdgePorts(edges: GraphLine[], nodes: GraphNode[]) {
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    for (const edge of edges) {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (source?.type !== GroupTypes.GROUP || target?.type !== GroupTypes.GROUP) {
        continue;
      }

      const { style: sourceStyle } = source;
      const { style: targetStyle } = target;
      // 垂直方向有重叠说明同一行左右排列，走左右边中点；
      // 否则上下错开（即使水平也错开，如访问冷节点），一律从上游下边中点连到下游上边中点
      const isSameRow = Math.abs(sourceStyle.y - targetStyle.y) < (sourceStyle.height + targetStyle.height) / 2;
      if (!isSameRow) {
        const isDown = targetStyle.y >= sourceStyle.y;
        edge.type = 'cubic-vertical';
        edge.style = {
          sourcePort: isDown ? 'bottom' : 'top',
          targetPort: isDown ? 'top' : 'bottom',
        };
      } else {
        const isRight = targetStyle.x >= sourceStyle.x;
        edge.type = 'cubic-horizontal';
        edge.style = {
          sourcePort: isRight ? 'right' : 'left',
          targetPort: isRight ? 'left' : 'right',
        };
      }
    }
  }

  /**
   * 单独处理 es master、cold、hot || hdfs hournal、zookeeper、datanode || mongo分片 节点水平排列
   * 以及 es clb 节点位置
   * @param nodes 节点列表
   */
  calcHorizontalAlignLocations(rootNodes: GraphNode[] = [], nodes: GraphNode[] = []) {
    const targetNodeIds = [
      nodeTypes.ES_MASTER,
      nodeTypes.ES_DATANODE_HOT,
      nodeTypes.ES_DATANODE_COLD,
      nodeTypes.HDFS_DATANODE,
      nodeTypes.HDFS_MASTER_HOURNALNODE,
      nodeTypes.HDFS_MASTER_ZOOKEEPER,
    ];
    // 历史多「分片xxx」组需要横排；合并后的 mongodb_shards 单组不含「分片」，天然不在此列
    const targetNodes = nodes.filter((node) => targetNodeIds.includes(node.id) || node.id.includes('分片'));

    const [referenceNode] = targetNodes;
    // Mongo 合并分片组、副本集等没有需要横排的节点
    if (referenceNode) {
      const moveNodes = targetNodes.slice(1);
      // 水平排列
      for (let i = 0; i < moveNodes.length; i++) {
        const node = moveNodes[i];
        const { width, x } = referenceNode.style;
        node.style.x = x + (width + this.nodeConfig.offsetX) * (i + 1);
      }
      // 整体向左偏移，让中间节点垂直对齐
      for (const node of targetNodes) {
        node.style.x = node.style.x - node.style.width - this.nodeConfig.offsetX;
        for (const childNode of node.children) {
          childNode.style.x = node.style.x;
        }
      }
    }

    // es clb 相关
    if (this.clusterType === ClusterTypes.ES) {
      const nodeMap = Object.fromEntries([...rootNodes, ...nodes].map((node) => [node.id, node]));

      const masterDomainNode = nodeMap[nodeTypes.MASTER_ENTRY_GROUP];

      const dnsDomainNode = nodeMap[nodeTypes.DNS_ENTRY_GROUP];
      const clbDomainNode = nodeMap[nodeTypes.CLB_DNS_ENTRY_GROUP];
      const clbIpNode = nodeMap[nodeTypes.CLB_ENTRY_GROUP];

      // 开启 clb / 恢复主域名直连接入层
      if (masterDomainNode && !dnsDomainNode && clbDomainNode && clbIpNode) {
        clbDomainNode.style.x = masterDomainNode.style.x - masterDomainNode.style.width - this.nodeConfig.offsetX;
        clbDomainNode.style.y = masterDomainNode.style.y;
        this.calcChildrenNodeLocations(clbDomainNode);

        clbIpNode.style.x = clbDomainNode.style.x;
        clbIpNode.style.y = clbDomainNode.style.y + clbDomainNode.style.height + this.nodeConfig.offsetY;
        this.calcChildrenNodeLocations(clbIpNode);
        return;
      }

      // 配置主域名指向 clb
      if (dnsDomainNode && clbDomainNode && clbIpNode) {
        clbDomainNode.style.x = dnsDomainNode.style.x - dnsDomainNode.style.width - this.nodeConfig.offsetX;
        clbDomainNode.style.y = dnsDomainNode.style.y;
        this.calcChildrenNodeLocations(clbDomainNode);

        // 此时北极星为单独的节点
        const polarisDomainNode = nodeMap[nodeTypes.MASTER_ENTRY_GROUP];
        if (polarisDomainNode) {
          polarisDomainNode.style.x = dnsDomainNode.style.x + dnsDomainNode.style.width + this.nodeConfig.offsetX;
          polarisDomainNode.style.y = dnsDomainNode.style.y;
          this.calcChildrenNodeLocations(polarisDomainNode);
        }
      }
    }
  }

  /**
   * 计算节点坐标：从每个根节点出发沿连线深度遍历，先到先定位
   * @param rootNodes 根节点（坐标已由 calcRootLocations 计算）
   * @param nodes 非根节点列表
   * @param lines 连线列表
   * @param avoidOverlap 是否避让重叠；有专属布局的集群类型会在之后重排节点，不做避让，避免临时位置把其它节点挤偏
   */
  calcNodeLocations(rootNodes: GraphNode[], nodes: GraphNode[], lines: GraphLine[], avoidOverlap: boolean) {
    const { offsetX, offsetY } = this.nodeConfig;
    const calculatedNodes = new Map<string, GraphNode>(rootNodes.map((node) => [node.id, node]));

    // 与已定位节点的矩形是否相交（坐标为中心点）
    const isOverlap = (targetNode: GraphNode) =>
      Array.from(calculatedNodes.values()).some(
        (node) =>
          Math.abs(node.style.x - targetNode.style.x) < (node.style.width + targetNode.style.width) / 2 &&
          Math.abs(node.style.y - targetNode.style.y) < (node.style.height + targetNode.style.height) / 2,
      );

    const updateNodeLocation = (startNode: GraphNode) => {
      const startLines = lines.filter((line) => line.source === startNode.id);
      for (const startLine of startLines) {
        const { isSameY, target } = startLine;
        const targetNode = nodes.find((node) => node.id === target);

        if (!targetNode || calculatedNodes.has(targetNode.id)) {
          continue;
        }

        const { height, width, x, y } = startNode.style;
        const heightDifference = (targetNode.style.height - height) / 2; // 渲染节点是以y值为中心，所以需要计算两个节点高度差的一半
        targetNode.style.x = isSameY ? x + width + offsetX : x;
        targetNode.style.y = isSameY ? y : y + height + offsetY + heightDifference;

        // 同一上游的多个下游会落到同一位置，依次向右平移到空位
        if (avoidOverlap) {
          while (isOverlap(targetNode)) {
            targetNode.style.x += targetNode.style.width + offsetX;
          }
        }

        this.calcChildrenNodeLocations(targetNode);
        calculatedNodes.set(targetNode.id, targetNode);
        updateNodeLocation(targetNode);
      }
    };

    // 只能由其它根节点到达的分组也要定位，否则会停在原点
    rootNodes.forEach((rootNode) => updateNodeLocation(rootNode));
  }

  /**
   * 按文案计算节点宽度，去掉短文案右侧的大片空白
   * 布局公式按节点等宽推导（如同行节点间距 x + width + offsetX），因此整张图取同一宽度，
   * 由最长的分组标题或实例文案决定，并限制在 [minWidth, width] 之间，超出最大宽度仍折行
   * Mongo 合并分片组文案特别长，单独计算，不拉宽其它节点
   */
  calcNodeWidths(data: ResourceTopo) {
    const { minWidth, mongoShardsWidth, width } = this.nodeConfig;
    const nodeMap = new Map(data.nodes.map((node) => [node.node_id, node]));
    // 文案左侧为图标区，右侧留白与左侧文字边距对称
    const getRequiredWidth = (textWidth: number) => Math.ceil(TEXT_LEFT_OFFSET + textWidth + TEXT_RIGHT_PADDING * 2);
    const getChildrenTextWidth = (childrenId: string[]) =>
      childrenId.reduce((maxWidth, id) => {
        const node = nodeMap.get(id);
        return node ? Math.max(maxWidth, measureTextWidth(formatTopoNodeName(node))) : maxWidth;
      }, 0);

    let textWidth = 0;
    let shardsTextWidth = 0;
    for (const group of data.groups) {
      const titleWidth = measureTextWidth(group.group_name || group.node_id, GROUP_TITLE_FONT);
      if (group.node_id === nodeTypes.MONGODB_SHARDS) {
        shardsTextWidth = Math.max(titleWidth, getChildrenTextWidth(group.children_id));
      } else {
        textWidth = Math.max(textWidth, titleWidth, getChildrenTextWidth(group.children_id));
      }
    }

    this.nodeWidth = _.clamp(getRequiredWidth(textWidth), minWidth, Math.max(minWidth, width));
    // 分片组不窄于普通节点，避免同列对齐时显得突兀
    this.mongoShardsNodeWidth = _.clamp(
      getRequiredWidth(shardsTextWidth),
      this.nodeWidth,
      Math.max(this.nodeWidth, mongoShardsWidth),
    );
  }

  /**
   * 计算根节点坐标
   * @param nodes 根节点
   */
  calcRootLocations(nodes: GraphNode[]) {
    const { offsetX, startX, startY } = this.nodeConfig;
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      node.style.x = (node.style.width + offsetX) * i + startX;
      node.style.y = startY;
      this.calcChildrenNodeLocations(node);
    }
  }

  /**
   * 处理 spider 中控节点、SpiderSlave 、运维节点位置
   * @param nodes 节点列表
   */
  calcSpiderNodeLocations(rootNodes: GraphNode[] = [], nodes: GraphNode[] = []) {
    const nodeMap = {} as Record<string, GraphNode>;
    for (const node of [...rootNodes, ...nodes]) {
      nodeMap[node.id] = node;
    }

    // 设置中控节点位置
    const controllerNode = nodeMap[nodeTypes.TENDBCLUSTER_CONTROLLER];
    const spiderMasterNode = nodeMap[nodeTypes.TENDBCLUSTER_MASTER];
    if (controllerNode && spiderMasterNode) {
      controllerNode.style.y = spiderMasterNode.style.y;
      controllerNode.style.x = spiderMasterNode.style.x - controllerNode.style.width - this.nodeConfig.offsetX;
      this.calcChildrenNodeLocations(controllerNode);
    }

    // 设置 SpiderSlave 节点位置
    const spiderSlaveEntryNode = nodeMap[nodeTypes.SPIDER_SLAVE_ENTRY_BIND];
    const spiderSlaveNode = nodeMap[nodeTypes.TENDBCLUSTER_SLAVE];
    if (spiderMasterNode && spiderSlaveEntryNode && spiderSlaveNode) {
      spiderSlaveNode.style.y = spiderMasterNode.style.y;
      spiderSlaveNode.style.x = spiderSlaveEntryNode.style.x;
      this.calcChildrenNodeLocations(spiderSlaveNode);
    }

    // 设置运维节点位置
    const mntNode = nodeMap[nodeTypes.TENDBCLUSTER_MNT];
    const referenceNode = nodeMap[nodeTypes.TENDBCLUSTER_REMOTE_MASTER];
    if (mntNode && referenceNode) {
      const { height, y } = referenceNode.style;
      const heightDifference = (mntNode.style.height - height) / 2;
      mntNode.style.y = y + height + this.nodeConfig.offsetY + heightDifference + 40;
      mntNode.style.x = referenceNode.style.x;
      this.calcChildrenNodeLocations(mntNode);
    }

    const masterDomainNode = nodeMap[nodeTypes.SPIDER_MASTER_ENTRY_BIND];
    const clbMasterDomainNode = nodeMap[nodeTypes.CLB_MASTER_DNS_ENTRY_GROUP];
    const clbMasterIpNode = nodeMap[nodeTypes.CLB_MASTER_ENTRY_GROUP];

    const slaveDomainNode = nodeMap[nodeTypes.SPIDER_SLAVE_ENTRY_BIND];
    const clbSlaveDomainNode = nodeMap[nodeTypes.CLB_SLAVE_DNS_ENTRY_GROUP];
    const clbSlaveIpNode = nodeMap[nodeTypes.CLB_SLAVE_ENTRY_GROUP];

    // 开启 clb / 恢复主域名直连接入层
    if (masterDomainNode && spiderMasterNode && clbMasterDomainNode && clbMasterIpNode) {
      clbMasterDomainNode.style.x = masterDomainNode.style.x - masterDomainNode.style.width - this.nodeConfig.offsetX;
      clbMasterDomainNode.style.y = masterDomainNode.style.y;
      this.calcChildrenNodeLocations(clbMasterDomainNode);

      clbMasterIpNode.style.x = spiderMasterNode.style.x - spiderMasterNode.style.width - this.nodeConfig.offsetX;
      clbMasterIpNode.style.y = spiderMasterNode.style.y;
      this.calcChildrenNodeLocations(clbMasterIpNode);

      // 中控节点需要继续向左移动防止遮挡
      if (controllerNode) {
        controllerNode.style.x = clbMasterIpNode.style.x - clbMasterIpNode.style.width - this.nodeConfig.offsetX;
        this.calcChildrenNodeLocations(controllerNode);
      }
    }
    if (slaveDomainNode && spiderSlaveNode && clbSlaveDomainNode && clbSlaveIpNode) {
      clbSlaveDomainNode.style.x = slaveDomainNode.style.x + slaveDomainNode.style.width + this.nodeConfig.offsetX;
      clbSlaveDomainNode.style.y = slaveDomainNode.style.y;
      this.calcChildrenNodeLocations(clbSlaveDomainNode);

      clbSlaveIpNode.style.x = spiderSlaveNode.style.x + spiderSlaveNode.style.width + this.nodeConfig.offsetX;
      clbSlaveIpNode.style.y = spiderSlaveNode.style.y;
      this.calcChildrenNodeLocations(clbSlaveIpNode);
    }

    const dnsMasterDomainNode = nodeMap[nodeTypes.DNS_MASTER_ENTRY_GROUP];
    const dnsSlaveDomainNode = nodeMap[nodeTypes.DNS_SLAVE_ENTRY_GROUP];

    // 配置域名指向 clb
    if (dnsMasterDomainNode && clbMasterDomainNode && clbMasterIpNode) {
      clbMasterDomainNode.style.x =
        dnsMasterDomainNode.style.x - dnsMasterDomainNode.style.width - this.nodeConfig.offsetX;
      clbMasterDomainNode.style.y = dnsMasterDomainNode.style.y;
      this.calcChildrenNodeLocations(clbMasterDomainNode);
    }
    if (dnsSlaveDomainNode && clbSlaveDomainNode && clbSlaveIpNode) {
      clbSlaveDomainNode.style.x =
        dnsSlaveDomainNode.style.x + dnsSlaveDomainNode.style.width + this.nodeConfig.offsetX;
      clbSlaveDomainNode.style.y = dnsSlaveDomainNode.style.y;
      this.calcChildrenNodeLocations(clbSlaveDomainNode);

      clbSlaveIpNode.style.x = dnsSlaveDomainNode.style.x;
      clbSlaveIpNode.style.y = dnsSlaveDomainNode.style.y + dnsSlaveDomainNode.style.height + this.nodeConfig.offsetY;
      this.calcChildrenNodeLocations(clbSlaveIpNode);

      // 原先的从域名失效，此时要以 clb 的域名为基准
      if (spiderMasterNode && dnsSlaveDomainNode && spiderSlaveNode) {
        spiderSlaveNode.style.y = spiderMasterNode.style.y;
        spiderSlaveNode.style.x = dnsSlaveDomainNode.style.x;
        this.calcChildrenNodeLocations(spiderSlaveNode);
      }
    }
  }

  /**
   * 处理 SurrealDB role 相关节点位置
   * @param nodes 节点列表
   */
  calcSurrealdbHaNodeLocations(rootNodes: GraphNode[] = [], nodes: GraphNode[] = []) {
    const nodeMap = {} as Record<string, GraphNode>;
    for (const node of [...rootNodes, ...nodes]) {
      nodeMap[node.id] = node;
    }

    const tikvNode = nodeMap[nodeTypes.TIKV];
    const pdNode = nodeMap[nodeTypes.PD];

    if (tikvNode && pdNode) {
      pdNode.style.y = tikvNode.style.y;
      pdNode.style.x = tikvNode.style.x + tikvNode.style.width + this.nodeConfig.offsetX;
      this.calcChildrenNodeLocations(pdNode);
    }
  }

  /**
   * 处理 tendbha clb 相关节点位置
   * @param nodes 节点列表
   */
  calcTendbHaNodeLocations(rootNodes: GraphNode[] = [], nodes: GraphNode[] = []) {
    const nodeMap = {} as Record<string, GraphNode>;
    for (const node of [...rootNodes, ...nodes]) {
      nodeMap[node.id] = node;
    }

    const masterDomainNode = nodeMap[nodeTypes.MASTER_ENTRY_GROUP];
    const proxyIpNode = nodeMap[nodeTypes.PROXY];

    const clbDomainNode = nodeMap[nodeTypes.CLB_DNS_ENTRY_GROUP];
    const clbIpNode = nodeMap[nodeTypes.CLB_ENTRY_GROUP];
    const dnsDomainNode = nodeMap[nodeTypes.DNS_ENTRY_GROUP];

    // 开启 clb / 恢复主域名直连接入层
    if (masterDomainNode && proxyIpNode && clbDomainNode && clbIpNode) {
      clbDomainNode.style.y = masterDomainNode.style.y;
      clbDomainNode.style.x = masterDomainNode.style.x - masterDomainNode.style.width - this.nodeConfig.offsetX;
      this.calcChildrenNodeLocations(clbDomainNode);

      clbIpNode.style.y = proxyIpNode.style.y;
      clbIpNode.style.x = proxyIpNode.style.x - proxyIpNode.style.width - this.nodeConfig.offsetX;
      this.calcChildrenNodeLocations(clbIpNode);
      return;
    }

    // 配置主域名指向 clb
    if (dnsDomainNode && clbDomainNode && clbIpNode) {
      clbDomainNode.style.y = dnsDomainNode.style.y;
      clbDomainNode.style.x = dnsDomainNode.style.x - dnsDomainNode.style.width - this.nodeConfig.offsetX;
      this.calcChildrenNodeLocations(clbDomainNode);
    }
  }

  /**
   * 处理 vm 标准集群 role 相关节点位置
   * @param nodes 节点列表
   */
  calcVmClusterNodeLocations(rootNodes: GraphNode[] = [], nodes: GraphNode[] = []) {
    const nodeMap = {} as Record<string, GraphNode>;
    for (const node of [...rootNodes, ...nodes]) {
      nodeMap[node.id] = node;
    }

    const vmInsertNode = nodeMap[nodeTypes.VMINSERT];
    const vmSelectNode = nodeMap[nodeTypes.VMSELECT];

    if (vmInsertNode && vmSelectNode) {
      vmSelectNode.style.y = vmInsertNode.style.y;
      vmSelectNode.style.x = vmInsertNode.style.x + vmInsertNode.style.width + this.nodeConfig.offsetX;
      this.calcChildrenNodeLocations(vmSelectNode);
    }
  }

  /**
   * 获取 graph 数据
   * @param data 集群拓扑数据
   * @param type 集群类型
   * @returns graph data
   */
  formatGraphData(data: ResourceTopo, dbType: string) {
    let edges: GraphLine[] = [];
    let nodes: GraphNode[] = [];
    if (dbType === DBTypes.RIAK) {
      nodes = data.nodes.map((item, index) => ({
        belong: '', // 节点所属组 ID
        children: [],
        data: item,
        id: item.node_id,
        name: formatTopoNodeName(item),
        style: {
          height: 44,
          width: 192,
          x: 100 + (index % 4) * 208,
          y: 100 + Math.floor(index / 4) * 56,
        },

        type: 'node', // 节点类型 group | node
      }));
    } else {
      this.calcNodeWidths(data);
      const rootGroups = this.getRootGroups(data, dbType);
      const groups = this.getGroups(data, rootGroups);
      const groupLines = getGroupLines(data);
      this.calcRootLocations(rootGroups);
      this.calcNodeLocations(rootGroups, groups, groupLines, !CUSTOM_LAYOUT_CLUSTER_TYPES.includes(this.clusterType));

      // es hdfs mongo 集群特殊逻辑
      if (HORIZONTAL_ALIGN_CLUSTER_TYPES.includes(this.clusterType)) {
        this.calcHorizontalAlignLocations(rootGroups, groups);
      } else if (this.clusterType === ClusterTypes.TENDBCLUSTER) {
        this.calcSpiderNodeLocations(rootGroups, groups);
      } else if (this.clusterType === ClusterTypes.TENDBHA) {
        this.calcTendbHaNodeLocations(rootGroups, groups);
      } else if (this.clusterType === ClusterTypes.K8S_SURREALDB_HA) {
        this.calcSurrealdbHaNodeLocations(rootGroups, groups);
      } else if (this.clusterType === ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER) {
        this.calcVmClusterNodeLocations(rootGroups, groups);
      }

      edges = getLines(data);
      nodes = [...rootGroups, ...groups].reduce<GraphNode[]>(
        (results, node) => results.concat([node], node.children),
        [],
      );
      this.calcEdgePorts(edges, nodes);
    }
    this.graphData = {
      edges,
      nodes,
    };

    return this.graphData;
  }

  /**
   * 获取非入口 groups
   * @param data 集群拓扑数据
   * @returns 非入口 groups
   */
  getGroups(data: ResourceTopo, roots: GraphNode[]): GraphNode[] {
    const { groups, nodes } = data;
    const rootIds = roots.map((node) => node.id);
    const results = [];
    for (const group of groups) {
      const { children_id: childrenId, group_name: groupName, node_id: nodeId } = group;
      if (!rootIds.includes(nodeId)) {
        const groupWidth = nodeId === nodeTypes.MONGODB_SHARDS ? this.mongoShardsNodeWidth : this.nodeWidth;
        // 子节点列表
        const children = childrenId
          .map((id) => {
            const node = nodes.find((node) => id === node.node_id);

            if (!node) {
              return null;
            }
            const name = formatTopoNodeName(node);
            return {
              belong: group.node_id,
              children: [],
              data: node,
              id: node.node_id,
              name,
              style: {
                // 文案折行时行高相应加高
                height: this.getNodeRowHeight(name, groupWidth),
                width: groupWidth,
                x: 0,
                y: 0,
              },
              type: GroupTypes.NODE,
            };
          })
          .filter((item) => item !== null) as GraphNode[];

        results.push({
          belong: '',
          children,
          data: group,
          id: nodeId,
          name: groupName || nodeId,
          style: {
            height: this.getNodeHeight(children),
            width: groupWidth,
            x: 0,
            y: 0,
          },
          type: GroupTypes.GROUP,
        });
      }
    }
    return results;
  }

  /**
   * 获取节点高度
   * @param data 节点 data
   * @returns 节点高度
   */
  getNodeHeight(data: GraphNode[]) {
    const { minHeight } = this.nodeConfig;

    // 子节点可能因文案折行而高于 itemHeight，按实际高度累加
    return minHeight + data.reduce((total, item) => total + item.style.height, 0);
  }

  /**
   * 获取实例行高度：按文案折行行数加高，单行仍为 itemHeight
   * @param name 节点文案
   * @param width 节点宽度
   * @returns 节点高度
   */
  getNodeRowHeight(name: string, width: number) {
    const lines = getWrapLineCount(name, width - TEXT_LEFT_OFFSET - TEXT_RIGHT_PADDING);

    return this.nodeConfig.itemHeight + (lines - 1) * TEXT_LINE_HEIGHT;
  }

  /**
   * 获取访问入口 groups
   * @param data 集群拓扑数据
   * @returns 访问入口 groups
   */
  getRootGroups(data: ResourceTopo, dbType: string): GraphNode[] {
    const { groups, lines, node_id: nodeId, nodes } = data;
    const rootLines = lines.filter(
      (line) =>
        !lines.some((l) => {
          if (line.source_type === 'node') {
            // return nodes.find(node => node.node_id === line.source)!.node_type === l.target;
            return true;
          }
          return l.target === line.source;
        }),
    );
    let roots = rootLines
      .map((line) => {
        const group = groups.find((group) => group.node_id === line.source);

        if (!group) {
          return null;
        }
        // 子节点列表
        const children = group.children_id
          .map((id) => {
            const node = nodes.find((node) => id === node.node_id);

            if (!node) {
              return null;
            }
            const name = formatTopoNodeName(node);
            return {
              belong: group.node_id,
              children: [],
              data: node,
              id: node.node_id,
              name,
              style: {
                // 文案折行时行高相应加高
                height: this.getNodeRowHeight(name, this.nodeWidth),
                width: this.nodeWidth,
                x: 0,
                y: 0,
              },
              type: GroupTypes.NODE,
            };
          })
          .filter((item) => item !== null) as GraphNode[];

        return {
          belong: '',
          children,
          data: group,
          id: group.node_id,
          name: group.group_name || group.node_id,
          style: {
            height: this.getNodeHeight(children),
            width: this.nodeWidth,
            x: 0,
            y: 0,
          },
          type: GroupTypes.GROUP,
        };
      })
      .filter((item) => item !== null) as GraphNode[];

    if (dbType === DBTypes.MONGODB) {
      return [roots[0]];
    }
    if (dbType === DBTypes.REDIS) {
      const clbDnsItem = roots.find((rootItem) => rootItem.id === nodeTypes.CLB_DNS_ENTRY_GROUP);
      if (clbDnsItem) {
        // TODO 可以优先在 formatGraphData 做特殊逻辑的节点位置计算
        const extractedRoots = roots.filter((item) => item.id !== nodeTypes.CLB_DNS_ENTRY_GROUP);
        const rootMap = extractedRoots.reduce<Record<string, GraphNode>>((prevMap, rootItem) => {
          if (prevMap[rootItem.id]) {
            return prevMap;
          }

          return Object.assign({}, prevMap, { [rootItem.id]: rootItem });
        }, {});
        roots = [clbDnsItem, ...Object.values(rootMap)];
        return roots;
      } else {
        const rootMap = roots.reduce<Record<string, GraphNode>>((prevMap, rootItem) => {
          if (prevMap[rootItem.id]) {
            return prevMap;
          }

          return Object.assign({}, prevMap, { [rootItem.id]: rootItem });
        }, {});
        roots = Object.values(rootMap);
      }
    }
    // 提前将clb相关节点提取到 roots 最后，防止 formatGraphData 做计算时会出现空白占位
    if (dbType === DBTypes.TENDBCLUSTER) {
      const extractedRoots: GraphNode[] = [];
      const clbRoots: GraphNode[] = [];
      roots.forEach((rootItem) => {
        if ([nodeTypes.CLB_MASTER_DNS_ENTRY_GROUP, nodeTypes.CLB_SLAVE_DNS_ENTRY_GROUP].includes(rootItem.id)) {
          clbRoots.push(rootItem);
        } else {
          extractedRoots.push(rootItem);
        }
      });
      return [...extractedRoots, ...clbRoots];
    }
    // 排序根节点
    // 包含集群主入口的根节点排最前，其余保持原顺序（sort 稳定）
    const hasMainEntry = (root: GraphNode) => Number(root.children.some((node) => node.id === nodeId));
    roots.sort((a, b) => hasMainEntry(b) - hasMainEntry(a));
    return roots;
  }
}
