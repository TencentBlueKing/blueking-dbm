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

// 节点连线结构
export interface GraphLine {
  id: string;
  isSameY: boolean;
  label: string;
  source: string;
  target: string;
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
  ES_DATANODE_COLD: 'es_datanode::es_datanode_cold',
  ES_DATANODE_HOT: 'es_datanode::es_datanode_hot',
  ES_MASTER: 'es_master::es_master',
  HDFS_DATANODE: 'hdfs_datanode::hdfs_datanode',
  HDFS_MASTER_HOURNALNODE: 'hdfs_master::hdfs_journalnode',
  HDFS_MASTER_NAMENODE: 'hdfs_master::hdfs_namenode',
  HDFS_MASTER_ZOOKEEPER: 'hdfs_master::hdfs_zookeeper',
  MASTER: 'backend::backend_master',
  MONGODB_BACKUP: 'mongodb::backup',
  MONGODB_CONFIG: 'mongo_config::m1',
  MONGODB_M1: 'mongodb::m1',
  MONGODB_M2: 'mongodb::m2',
  MONGODB_MONGOS: 'mongos',
  PULSAR_BOOKKEEPER: 'pulsar_bookkeeper::pulsar_bookkeeper',
  PULSAR_BROKER: 'pulsar_broker::pulsar_broker',
  PULSAR_ZOOKEEPER: 'pulsar_zookeeper::pulsar_zookeeper',
  SLAVE: 'backend::backend_slave',
  SPIDER_SLAVE_ENTRY_BIND: 'spider_slave_entry_bind',
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
};

type GroupTypesStrings = `${GroupTypes}`;

const defaultNodeConfig = {
  groupTitle: 44,
  itemHeight: 28,
  minHeight: 54,
  offsetX: 140,
  offsetY: 62,
  startX: 100,
  startY: 100,
  width: 296,
};

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
      sourceGroup && (sourceId = sourceGroup.node_id);
    } else if (targetType === 'node') {
      // 处理 target 为 node 的情况
      const targetGroup = groups.find((group) => group.children_id.includes(target));
      targetGroup && (targetId = targetGroup.node_id);
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

  nodeConfig: typeof defaultNodeConfig = { ...defaultNodeConfig };

  constructor(clusterType: string, nodeConfig: NodeConfig = {}) {
    this.nodeConfig = Object.assign(this.nodeConfig, nodeConfig);
    this.clusterType = clusterType;
  }

  /**
   * 设置 children locations
   */
  calcChildrenNodeLocations(targetNode: GraphNode) {
    const { groupTitle, itemHeight } = this.nodeConfig;
    targetNode.children.forEach((childNode, index) => {
      const offet = (targetNode.style.height - childNode.style.height) / 2;
      // eslint-disable-next-line no-param-reassign
      childNode.style.x = targetNode.style.x;
      // eslint-disable-next-line no-param-reassign
      childNode.style.y =
        index === 0 ? targetNode.style.y + groupTitle - offet : targetNode.children[index - 1].style.y + itemHeight;
    });
  }

  /**
   * 单独处理 es master、cold、hot || hdfs hournal、zookeeper、datanode || mongo分片 节点水平排列
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
    const targetNodes = nodes.filter((node) => targetNodeIds.includes(node.id) || node.id.includes('分片'));

    const [referenceNode] = targetNodes;
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

  /**
   * 获取连线坐标
   * @param lines 连线集合
   * @param nodes 节点集合
   */
  calcLines(lines: GraphLine[], nodes: GraphNode[]) {
    for (const line of lines) {
      const source = nodes.find((node) => node.id === line.source);
      const target = nodes.find((node) => node.id === line.target);

      if (source) {
        Object.assign(line.source, {
          x: source.style.x || 0,
          y: source.style.y || 0,
        });
      }
      if (target) {
        Object.assign(line.target, {
          x: target.style.x || 0,
          y: target.style.y || 0,
        });
      }
    }
  }

  /**
   * 计算节点坐标
   * @param startNode 开始节点
   * @param nodes 节点列表
   * @param lines 连线列表
   * @param calculatedNodes 存储已经计算过的节点
   */
  calcNodeLocations(startNode: GraphNode, nodes: GraphNode[], lines: GraphLine[]) {
    const calculatedNodes: Map<string, GraphNode> = new Map<string, GraphNode>();

    const updateNodeLocation = (startNode: GraphNode, nodes: GraphNode[], lines: GraphLine[]) => {
      if (!startNode) {
        return;
      }

      calculatedNodes.set(startNode.id, startNode);
      const startLines = lines.filter((line) => line.source === startNode.id);
      for (const startLine of startLines) {
        const { isSameY, target } = startLine;
        const targetNode = nodes.find((node) => node.id === target);

        if (targetNode && !calculatedNodes.get(targetNode.id)) {
          const { height, width, x, y } = startNode.style;
          const { groupTitle, itemHeight, offsetX, offsetY } = this.nodeConfig;
          const heightDifference = (targetNode.style.height - height) / 2; // 渲染节点是以y值为中心，所以需要计算两个节点高度差的一半
          targetNode.style.x = isSameY ? x + width + offsetX : x;
          targetNode.style.y = isSameY ? y : y + height + offsetY + heightDifference;

          // 计算 children nodes 坐标
          targetNode.children.forEach((childNode, index) => {
            const offet = (targetNode.style.height - childNode.style.height) / 2;
            // eslint-disable-next-line no-param-reassign
            childNode.style.x = targetNode.style.x;
            // eslint-disable-next-line no-param-reassign
            childNode.style.y =
              index === 0
                ? targetNode.style.y + groupTitle - offet
                : targetNode.children[index - 1].style.y + itemHeight;
          });

          calculatedNodes.set(targetNode.id, targetNode);
          updateNodeLocation(targetNode, nodes, lines);
        }
      }
    };

    updateNodeLocation(startNode, nodes, lines);
  }

  /**
   * 计算根节点坐标
   * @param nodes 根节点
   */
  calcRootLocations(nodes: GraphNode[]) {
    const { groupTitle, itemHeight, offsetX, startX, startY } = this.nodeConfig;
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      node.style.x = (node.style.width + offsetX) * i + startX;
      node.style.y = startY;

      // 计算 children nodes 坐标
      node.children.forEach((childNode, index) => {
        const offet = (node.style.height - childNode.style.height) / 2;
        // eslint-disable-next-line no-param-reassign
        childNode.style.x = node.style.x;
        // eslint-disable-next-line no-param-reassign
        childNode.style.y =
          index === 0 ? node.style.y + groupTitle - offet : node.children[index - 1].style.y + itemHeight;
      });
    }
  }

  /**
   * 处理 spider 中控节点、运维节点位置
   * @param nodes 节点列表
   */
  calcSpiderNodeLocations(rootNodes: GraphNode[] = [], nodes: GraphNode[] = []) {
    const nodeMap = {} as Record<string, GraphNode>;
    for (const node of [...rootNodes, ...nodes]) {
      nodeMap[node.id] = node;
    }

    // 设置中控节点节点位置
    const controllerNode = nodeMap[nodeTypes.TENDBCLUSTER_CONTROLLER];
    const spiderMasterNode = nodeMap[nodeTypes.TENDBCLUSTER_MASTER];
    if (controllerNode && spiderMasterNode) {
      controllerNode.style.y = spiderMasterNode.style.y;
      controllerNode.style.x = -controllerNode.style.width;
      this.calcChildrenNodeLocations(controllerNode);
    }

    const spiderSlaveEntryNode = nodeMap[nodeTypes.SPIDER_SLAVE_ENTRY_BIND];
    const spiderSlaveNode = nodeMap[nodeTypes.TENDBCLUSTER_SLAVE];
    if (spiderMasterNode && spiderSlaveEntryNode && spiderSlaveNode) {
      spiderSlaveNode.style.y = spiderMasterNode.style.y;
      spiderSlaveNode.style.x = spiderSlaveEntryNode.style.x;
      this.calcChildrenNodeLocations(spiderSlaveNode);
    }

    const mntNode = nodeMap[nodeTypes.TENDBCLUSTER_MNT];
    const referenceNode = nodeMap[nodeTypes.TENDBCLUSTER_REMOTE_MASTER];
    if (mntNode && referenceNode) {
      const { height, y } = referenceNode.style;
      const heightDifference = (mntNode.style.height - height) / 2;
      mntNode.style.y = y + height + this.nodeConfig.offsetY + heightDifference + 40;
      mntNode.style.x = referenceNode.style.x;
      this.calcChildrenNodeLocations(mntNode);
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
        name: item.node_id,
        style: {
          height: 44,
          width: 192,
          x: 100 + (index % 4) * 208,
          y: 100 + Math.floor(index / 4) * 56,
        },

        type: 'node', // 节点类型 group | node
      }));
    } else {
      const rootGroups = this.getRootGroups(data, dbType);
      const groups = this.getGroups(data, rootGroups);
      const groupLines = getGroupLines(data);
      this.calcRootLocations(rootGroups);
      const [firstRoot] = rootGroups;
      this.calcNodeLocations(firstRoot, groups, groupLines);

      // es hdfs mongo 集群特殊逻辑
      if (([ClusterTypes.ES, ClusterTypes.HDFS, ClusterTypes.MONGODB] as string[]).includes(this.clusterType)) {
        this.calcHorizontalAlignLocations(groups);
      } else if (this.clusterType === ClusterTypes.TENDBCLUSTER) {
        this.calcSpiderNodeLocations(rootGroups, groups);
      }

      edges = getLines(data);
      nodes = [...rootGroups, ...groups].reduce<GraphNode[]>(
        (results, node) => results.concat([node], node.children),
        [],
      );
      this.calcLines(edges, nodes);
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
        // 子节点列表
        const children = childrenId
          .map((id) => {
            const node = nodes.find((node) => id === node.node_id);

            if (!node) {
              return null;
            }
            return {
              belong: group.node_id,
              children: [],
              data: node,
              id: node.node_id,
              name: node.node_id,
              style: {
                height: this.nodeConfig.itemHeight,
                width: this.nodeConfig.width,
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
            width: this.nodeConfig.width,
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
    const nums = data.length;
    const { itemHeight, minHeight } = this.nodeConfig;

    return minHeight + itemHeight * nums;
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
        // 子节点列表
        const children = group.children_id
          .map((id) => {
            const node = nodes.find((node) => id === node.node_id);

            if (!node) {
              return null;
            }
            return {
              belong: group.node_id,
              children: [],
              data: node,
              id: node.node_id,
              name: node.node_id,
              style: {
                height: this.nodeConfig.itemHeight,
                width: this.nodeConfig.width,
                x: 0,
                y: 0,
              },
              type: GroupTypes.NODE,
            };
          })
          .filter((item) => item !== null);

        return {
          belong: '',
          children,
          data: group,
          id: group.node_id,
          name: group.group_name || group.node_id,
          style: {
            height: this.getNodeHeight(children as GraphNode[]),
            width: this.nodeConfig.width,
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
      const clbDnsItem = roots.find((rootItem) => rootItem.id === 'clb_dns_entry_group');
      if (clbDnsItem) {
        const extractedRoots = roots.filter((item) => item.id !== 'clb_dns_entry_group');
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
    // 排序根节点
    roots.sort((a) => (a.children.find((node) => node.id === nodeId) ? -1 : 0));
    return roots;
  }
}
