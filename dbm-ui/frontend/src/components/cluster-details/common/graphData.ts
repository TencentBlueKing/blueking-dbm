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

import type { ResourceTopo, ResourceTopoGroup, ResourceTopoNode } from '@services/types/clusters';

const defaultNodeConfig = {
  width: 296,
  itemHeight: 28,
  minHeight: 54,
  offsetX: 140,
  offsetY: 62,
  startX: 100,
  startY: 100,
  groupTitle: 44,
};
export type NodeConfig = Partial<typeof defaultNodeConfig>;

// 节点连线结构
export interface GraphLine {
  id: string,
  isSameY: boolean,
  label: string,
  source: { id: string, x: number, y: number },
  target: { id: string, x: number, y: number },
}

// graph node types
export enum GroupTypes {
  GROUP = 'group',
  NODE = 'node'
}
type GroupTypesStrings = `${GroupTypes}`;

// 节点返回数据结构
export interface GraphNode {
  id: string,
  label: string,
  data: ResourceTopoNode | ResourceTopoGroup,
  children: GraphNode[],
  width: number,
  height: number,
  x: number,
  y: number
  type: GroupTypesStrings, // 节点类型 group | node
  belong: string, // 节点所属组 ID
}

export interface GraphInstance {
  _diagramInstance?: {
    _canvas?: any
  }
}

// 节点类型
export const nodeTypes = {
  MASTER: 'backend::backend_master',
  SLAVE: 'backend::backend_slave',
  TENDISCACHE_MASTER: 'tendiscache::redis_master',
  TENDISCACHE_SLAVE: 'tendiscache::redis_slave',
  TENDISPLUS_MASTER: 'tendisplus::redis_master',
  TENDISPLUS_SLAVE: 'tendisplus::redis_slave',
  TENDISSSD_MASTER: 'tendisssd::redis_master',
  TENDISSSD_SLAVE: 'tendisssd::redis_slave',
  HDFS_MASTER_NAMENODE: 'hdfs_master::hdfs_namenode',
  HDFS_MASTER_HOURNALNODE: 'hdfs_master::hdfs_journalnode',
  HDFS_MASTER_ZOOKEEPER: 'hdfs_master::hdfs_zookeeper',
  HDFS_DATANODE: 'hdfs_datanode::hdfs_datanode',
  ES_MASTER: 'es_master::es_master',
  ES_DATANODE_HOT: 'es_datanode::es_datanode_hot',
  ES_DATANODE_COLD: 'es_datanode::es_datanode_cold',
  PULSAE_BROKER: 'pulsar_broker::pulsar_broker',
  PULSAE_BOOKKEEPER: 'pulsar_bookkeeper::pulsar_bookkeeper',
  PULSAE_ZOOKEEPER: 'pulsar_zookeeper::pulsar_zookeeper',
};

// 特殊逻辑：控制节点水平对齐
const sameSources = [
  nodeTypes.MASTER,
  nodeTypes.TENDISCACHE_MASTER,
  nodeTypes.TENDISPLUS_MASTER,
  nodeTypes.TENDISSSD_MASTER,
  nodeTypes.PULSAE_BROKER,
];
const sameTargets = [
  nodeTypes.SLAVE,
  nodeTypes.TENDISCACHE_SLAVE,
  nodeTypes.TENDISPLUS_SLAVE,
  nodeTypes.TENDISSSD_SLAVE,
  nodeTypes.PULSAE_ZOOKEEPER,
];

export class GraphData {
  nodeConfig: typeof defaultNodeConfig = { ...defaultNodeConfig };
  clusterType: string;
  graphData: {
    locations: GraphNode[],
    lines: GraphLine[],
  } = { locations: [], lines: [] };

  constructor(clusterType: string, nodeConfig: NodeConfig = {}) {
    this.nodeConfig = Object.assign(this.nodeConfig, nodeConfig);
    this.clusterType = clusterType;
  }

  /**
   * 获取 graph 数据
   * @param data 集群拓扑数据
   * @param type 集群类型
   * @returns graph data
   */
  formatGraphData(data: ResourceTopo) {
    const rootGroups = this.getRootGroups(data);
    const groups = this.getGroups(data, rootGroups);
    const groupLines = this.getGroupLines(data);
    this.calcRootLocations(rootGroups);
    const [firstRoot] = rootGroups;
    this.calcNodeLocations(firstRoot, groups, groupLines);

    // es 集群特殊逻辑
    if (['es', 'hdfs'].includes(this.clusterType)) {
      this.calcHorizontalAlignLocations(groups);
    }

    const lines = this.getLines(data);
    const locations: GraphNode[] = [...rootGroups, ...groups].reduce((nodes: GraphNode[], node) => (
      nodes.concat([node], node.children)
    ), []);
    this.calcLines(lines, locations);

    // format url
    for (const node of locations) {
      if (node.type === GroupTypes.NODE) {
        const { url } = node.data as ResourceTopoNode;
        if (url) {
          (node.data as ResourceTopoNode).url = escape(url);
        }
      }
    }

    this.graphData = {
      locations,
      lines,
    };

    return this.graphData;
  }

  /**
   * 获取访问入口 groups
   * @param data 集群拓扑数据
   * @returns 访问入口 groups
   */
  getRootGroups(data: ResourceTopo): GraphNode[] {
    const { node_id: nodeId, nodes, groups, lines } = data;
    const rootLines = lines.filter(line => !lines.some((l) => {
      if (line.source_type === 'node') {
        // return nodes.find(node => node.node_id === line.source)!.node_type === l.target;
        return true;
      }
      return l.target === line.source;
    }));
    const roots = rootLines.map((line) => {
      const group = groups.find(group => group.node_id === line.source);
      if (!group) return null;
      // 子节点列表
      const children = group.children_id.map((id) => {
        const node = nodes.find(node => id === node.node_id);
        if (!node) return null;
        return {
          id: node.node_id,
          data: node,
          width: this.nodeConfig.width,
          height: this.nodeConfig.itemHeight,
          belong: group.node_id,
          type: GroupTypes.NODE,
          label: '',
          x: 0,
          y: 0,
          children: [],
        };
      }).filter(item => item !== null);

      return {
        id: group.node_id,
        label: group.group_name,
        data: group,
        children,
        width: this.nodeConfig.width,
        height: this.getNodeHeight(children as GraphNode[]),
        type: GroupTypes.GROUP,
        belong: '',
        x: 0,
        y: 0,
      };
    }).filter(item => item !== null) as GraphNode[];
    // 排序根节点
    roots.sort(a => (a.children.find(node => node.id === nodeId) ? -1 : 0));
    return roots;
  }

  /**
   * 获取非入口 groups
   * @param data 集群拓扑数据
   * @returns 非入口 groups
   */
  getGroups(data: ResourceTopo, roots: GraphNode[]): GraphNode[] {
    const { groups, nodes } = data;
    const rootIds = roots.map(node => node.id);
    const results = [];
    for (const group of groups) {
      const { node_id: nodeId, children_id: childrenId, group_name: groupName } = group;
      if (!rootIds.includes(nodeId)) {
        // 子节点列表
        const children = childrenId.map((id) => {
          const node = nodes.find(node => id === node.node_id);
          if (!node) return null;
          return {
            id: node.node_id,
            data: node,
            width: this.nodeConfig.width,
            height: this.nodeConfig.itemHeight,
            belong: group.node_id,
            type: GroupTypes.NODE,
            label: '',
            x: 0,
            y: 0,
            children: [],
          };
        }).filter(item => item !== null) as GraphNode[];

        results.push({
          id: nodeId,
          label: groupName || nodeId,
          data: group,
          children,
          width: this.nodeConfig.width,
          height: this.getNodeHeight(children),
          type: GroupTypes.GROUP,
          x: 0,
          y: 0,
          belong: '',
        });
      }
    }
    return results;
  }

  /**
   * group lines
   * @param data 集群拓扑数据
   * @returns 获取 group 间连线
   */
  getGroupLines(data: ResourceTopo): GraphLine[] {
    const { lines, groups } = data;
    const results: GraphLine[] = [];

    for (const line of lines) {
      const {
        source,
        source_type: sourceType,
        target,
        target_type: targetType,
        label_name: labelName,
      } = line;
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
        const sourceGroup = groups.find(group => group.children_id.includes(source));
        sourceGroup && (sourceId = sourceGroup.node_id);
      } else if (targetType === 'node') {
        // 处理 target 为 node 的情况
        const targetGroup = groups.find(group => group.children_id.includes(target));
        targetGroup && (targetId = targetGroup.node_id);
      }
      results.push({
        id: `${sourceId}__${targetId}`,
        label: labelName,
        // source 为 master 且 target 为 slave 则 y 值相等
        isSameY: sameSources.includes(sourceId) && sameTargets.includes(targetId), // TODO: 这里是节点并列特殊逻辑
        source: { id: sourceId, x: 0, y: 0 },
        target: { id: targetId, x: 0, y: 0 },
      });
    }
    return results;
  }


  /**
   * 获取实际画图连线
   * @param data 集群拓扑数据
   * @returns GraphLines
   */
  getLines(data: ResourceTopo): GraphLine[] {
    const { lines } = data;
    const results = [];

    for (const line of lines) {
      const {
        source,
        target,
        label_name: labelName,
      } = line;
      const sourceId = source;
      const targetId = target;

      results.push({
        id: `${sourceId}__${targetId}`,
        label: labelName,
        // source为master且target为slave 则 y 值相等
        isSameY: sameSources.includes(sourceId) && sameTargets.includes(targetId), // TODO: 这里是节点并列特殊逻辑
        source: { id: sourceId, x: 0, y: 0 },
        target: { id: targetId, x: 0, y: 0 },
      });
    }
    return _.uniqBy(results, 'id');
  }

  /**
   * 获取节点高度
   * @param data 节点 data
   * @returns 节点高度
   */
  getNodeHeight(data: GraphNode[]) {
    const nums = data.length;
    const { minHeight, itemHeight } = this.nodeConfig;

    return minHeight + (itemHeight * nums);
  }

  /**
   * 计算根节点坐标
   * @param nodes 根节点
   */
  calcRootLocations(nodes: GraphNode[]) {
    const {
      offsetX,
      startX,
      startY,
      groupTitle,
      itemHeight,
    } = this.nodeConfig;
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      node.x = (node.width + offsetX) * i + startX;
      node.y = startY;

      // 计算 children nodes 坐标
      node.children.forEach((childNode, index) => {
        const offet = (node.height - childNode.height) / 2;
        // eslint-disable-next-line no-param-reassign
        childNode.x = node.x;
        // eslint-disable-next-line no-param-reassign
        childNode.y = index === 0 ? node.y + groupTitle - offet : node.children[index - 1].y + itemHeight;
      });
    }
  }

  /**
   * 计算节点坐标
   * @param startNode 开始节点
   * @param nodes 节点列表
   * @param lines 连线列表
   * @param calculatedNodes 存储已经计算过的节点
   */
  calcNodeLocations(
    startNode: GraphNode,
    nodes: GraphNode[],
    lines: GraphLine[],
    calculatedNodes = new Map<string, GraphNode>(),
  ) {
    const startLines = lines.filter(line => line.source.id === startNode.id);
    calculatedNodes.set(startNode.id, startNode);

    for (const startLine of startLines) {
      const { target, isSameY } = startLine;
      const targetNode = nodes.find(node => node.id === target.id);

      if (targetNode && !calculatedNodes.get(targetNode.id)) {
        const { x, y, height, width } = startNode;
        const {
          offsetX,
          offsetY,
          groupTitle,
          itemHeight,
        } = this.nodeConfig;
        const heightDifference = (targetNode.height - height) / 2; // 渲染节点是以y值为中心，所以需要计算两个节点高度差的一半
        targetNode.x = isSameY ? x + width + offsetX : x;
        targetNode.y = isSameY ? y : y + height + offsetY + heightDifference;

        // 计算 children nodes 坐标
        targetNode.children.forEach((childNode, index) => {
          const offet = (targetNode.height - childNode.height) / 2;
          // eslint-disable-next-line no-param-reassign
          childNode.x = targetNode.x;
          // eslint-disable-next-line no-param-reassign
          childNode.y = index === 0 ? targetNode.y + groupTitle - offet : targetNode.children[index - 1].y + itemHeight;
        });

        calculatedNodes.set(targetNode.id, targetNode);
        this.calcNodeLocations(targetNode, nodes, lines, calculatedNodes);
      }
    }
  }

  /**
   * 获取连线坐标
   * @param lines 连线集合
   * @param nodes 节点集合
   */
  calcLines(lines: GraphLine[], nodes: GraphNode[]) {
    for (const line of lines) {
      const source = nodes.find(node => node.id === line.source.id);
      const target = nodes.find(node => node.id === line.target.id);

      if (source) {
        Object.assign(line.source, {
          x: source.x || 0,
          y: source.y || 0,
        });
      }
      if (target) {
        Object.assign(line.target, {
          x: target.x || 0,
          y: target.y || 0,
        });
      }
    }
  }

  /**
   * 单独处理 es master、cold、hot || hdfs hournal、zookeeper、datanode 节点水平排列
   * @param nodes 节点列表
   */
  calcHorizontalAlignLocations(nodes: GraphNode[] = []) {
    const targetNodeIds = [
      nodeTypes.ES_MASTER,
      nodeTypes.ES_DATANODE_HOT,
      nodeTypes.ES_DATANODE_COLD,
      nodeTypes.HDFS_DATANODE,
      nodeTypes.HDFS_MASTER_HOURNALNODE,
      nodeTypes.HDFS_MASTER_ZOOKEEPER,
    ];
    const targetNodes = nodes.filter(node => targetNodeIds.includes(node.id));

    const [referenceNode] = targetNodes;
    const moveNodes = targetNodes.slice(1);
    // 水平排列
    for (let i = 0; i < moveNodes.length; i++) {
      const node = moveNodes[i];
      const { x, width } = referenceNode;
      node.x = x + (width + this.nodeConfig.offsetX) * (i + 1);
    }
    // 整体向左偏移，让中间节点垂直对齐
    for (const node of targetNodes) {
      node.x = node.x - node.width - this.nodeConfig.offsetX;
      for (const childNode of node.children) {
        childNode.x = node.x;
      }
    }
  }
}
