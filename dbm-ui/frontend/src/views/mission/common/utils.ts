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

import {
  type FlowItem,
  type FlowLine,
  type FlowsData,
  type FlowType,
  FlowTypes,
} from '@services/types/taskflow';

import type { RenderCollectionKey } from './graphRender';

export type RenderKey = 'start_event' | 'end_event' | 'activities' | 'gateways';
export interface GraphNode {
  id: string,
  tpl: RenderCollectionKey,
  data: FlowItem,
  width: number,
  height: number,
  level: number,
  isExpand: boolean,
  index: number,
  parent: null | GraphNode
  x?: number,
  y?: number,
  children?: GraphNode[][],
}
export interface GraphLine {
  id: string,
  source: { id: string, x?: number, y?: number },
  target: { id: string, x?: number, y?: number },
}

const getewayTypes: FlowType[] = [FlowTypes.ParallelGateway, FlowTypes.ConvergeGateway];
const bothEndTypes: FlowType[] = [FlowTypes.EmptyStartEvent, FlowTypes.EmptyEndEvent];

/**
 * 获取节点连线目标
 * @param node 当前节点
 * @param nodeMap 节点映射
 * @param flows 连线信息
 * @param isCurrent 是否返回当前节点
 * @param targets 节点连线目标
 * @returns targets
 */
const getLineTargets = (
  node: FlowItem,
  nodeMap: { [key: string]: FlowItem },
  flows: { [key: string]: FlowLine },
  isCurrent = false,
  targets: string[] = [],
): string[] => {
  const { outgoing, type } = node;
  // 返回当前节点
  if (isCurrent && !getewayTypes.includes(type)) {
    targets.push(node.id);
    return targets;
  }

  if (outgoing === '') return targets;

  if (Array.isArray(outgoing)) {
    outgoing.forEach((id: string) => {
      getLineTargets(nodeMap[flows[id].target], nodeMap, flows, true, targets);
    });

    return targets;
  }

  const targetNode = nodeMap[flows[outgoing].target];

  if (getewayTypes.includes(targetNode.type)) {
    return getLineTargets(targetNode, nodeMap, flows, false, targets);
  }
  targets.push(targetNode.id);
  return targets;
};

/**
 * 格式化画布连线
 * @param data 任务流程数据
 * @param level 层级
 * @param lines 画布渲染 lines
 * @returns lines
 */
const formartLines = (data: FlowsData, level = 0, lines: GraphLine[] = []) => {
  const {
    gateways,
    activities,
    end_event: endNode,
    start_event: startNode,
    flows,
  } = data;
  // 当层节点映射
  const nodesMap = {
    ...gateways,
    ...activities,
    [startNode.id]: startNode,
    [endNode.id]: endNode,
  };
  /**
   * nodeId: lineId mapping
   */
  const linesMap: { [nodeId: string]: string } = {};
  for (const flowLine of Object.values(flows)) {
    linesMap[flowLine.source] = flowLine.id;
  }

  for (const node of Object.values(nodesMap)) {
    /**
     * 1. 如果是 geteway 节点则不处理
     * 2. 子流程 end 节点不处理
     */
    if (getewayTypes.includes(node.type) || (node.type === FlowTypes.EmptyEndEvent && level > 0)) {
      continue;
    }

    // 处理子流程 start 节点
    if (node.type === FlowTypes.EmptyStartEvent && level > 0) {
      const { outgoing } = node;
      const addLine = (lineId: string) => {
        const { target } = flows[lineId];
        const targets = getLineTargets(nodesMap[target], nodesMap, flows, true);
        for (const id of targets) {
          lines.push({
            id: flows[lineId].id,
            source: { id: data.id },
            target: { id },
          });
        }
      };
      if (typeof outgoing === 'string') {
        addLine(outgoing);
        continue;
      }
      for (const lineId of outgoing) {
        addLine(lineId);
      }
      continue;
    }

    const targets = getLineTargets(node, nodesMap, flows);
    for (const id of targets) {
      lines.push({
        id: linesMap[id],
        source: { id: node.id },
        target: { id },
      });
    }

    if (node.pipeline) {
      formartLines(node.pipeline, level + 1, lines);
    }
  }

  return lines;
};

/**
 * 格式化节点数据
 * @param data 任务流程数据
 * @param expandNodes 展开节点ID列表
 * @returns {
 *  locations,
 *  lines
 * }
 */
export const formatGraphData = (data: FlowsData, expandNodes: string[] = []) => {
  const rootNodes = getLevelNodes(data, null, 0, expandNodes); // 所有根节点
  const bothEndNodes = []; // 开始、结束根节点
  const roots = []; // 非开始、结束的根节点
  // 分离开始、结束根节点
  for (const nodes of rootNodes) {
    if (nodes.some(node => bothEndTypes.includes(node.data.type))) {
      bothEndNodes.push(nodes);
    } else {
      roots.push(nodes);
    }
  }
  // 获取子节点
  getNodeChildren(roots, expandNodes);
  // 初始化根节点 x 位置
  initRootNodesX(rootNodes);
  // 计算节点位置
  calcNodesLocation(roots, expandNodes);
  // 扁平化节点
  const flagNodes: GraphNode[] = [];
  getFlagNodes(rootNodes, flagNodes, expandNodes);
  // 计算结束节点 x 值
  calcEndNodeLocationX(flagNodes);

  // 处理连线坐标
  const lines = formartLines(data);
  const renderLines = getRenderLines(lines, flagNodes);

  return reactive({
    locations: flagNodes, // 渲染根节点
    lines: renderLines,
  });
};

function getRenderLines(lines: GraphLine[], nodes: GraphNode[]) {
  const renderLines: GraphLine[] = [];
  for (const line of lines) {
    const newLine = _.cloneDeep(line);
    const { source, target } = newLine;
    const sourceNode = findTargetNode(source.id, nodes);
    const targetNode = findTargetNode(target.id, nodes);

    if (sourceNode && targetNode) {
      const isLowerLevel = sourceNode.level !== targetNode.level; // 节点不属于同一层
      const { x: sourceX = 0, y: sourceY = 0, width: sourceWidth } = sourceNode;
      const { x: targetX = 0, y: targetY = 0, width: targetWidth, height: targetHeight } = targetNode;
      const sourceOffsetX = (sourceWidth / 2) - 14 - 24;
      const targetOffsetX = targetWidth / 2;
      Object.assign(source, {
        x: isLowerLevel ? sourceX - sourceOffsetX : sourceX,
        y: sourceY,
      });
      Object.assign(target, {
        x: isLowerLevel ? targetX - targetOffsetX : targetX,
        y: isLowerLevel ? targetY + (targetHeight / 2) : targetY,
      });
      renderLines.push(newLine);
    }
  }
  return renderLines;
}

/**
 * 查询目标节点
 * @param id 节点ID
 * @returns 返回目标节点 | undefined
 */
function findTargetNode(id: string, nodes: GraphNode[]) {
  return nodes.find(node => node.id === id);
}

/**
 * 获取扁平化节点列表
 * @param nodes 节点列表
 * @param flagNodes 递归扁平化节点列表
 * @param expandNodes 展开节点ID列表
 */
function getFlagNodes(nodes: GraphNode[][], flagNodes: GraphNode[] = [], expandNodes: string[] = []) {
  for (const columnNodes of nodes) {
    for (const node of columnNodes) {
      flagNodes.push(node);

      if (node.children && expandNodes.includes(node.id) && node.children.length > 0) {
        getFlagNodes(node.children, flagNodes, expandNodes);
      }
    }
  }
}

const config = {
  horizontalSep: 100, // 节点水平间距
  verticalSep: 36, // 节点垂直间距
  chidlOffset: 66, // 子节点 x 偏移量
};

/**
 * 添加节点到当前层级的列中
 * @param node 当前节点信息
 * @param parent 父级节点信息
 * @param nodes 当层每列节点信息
 * @param index 列序号
 * @param level 节点层级
 */
function addNode(
  node: FlowItem,
  parent: null | GraphNode = null,
  nodes: GraphNode[][],
  index: number,
  level: number,
  expandNodes: string[] = [],
) {
  const isRoundType = bothEndTypes.includes(node.type);
  const len = nodes[index].length;
  const graphNode: GraphNode = {
    id: node.id,
    tpl: isRoundType ? 'round' : 'ractangle',
    data: node,
    width: isRoundType ? 48 : 280,
    height: 48,
    index: len,
    level,
    parent,
    isExpand: expandNodes.includes(node.id),
  };
  nodes[index].push(graphNode);
}

/**
 * 获取当层每列节点信息
 * @param data 当层 flow 数据
 * @param parent 父节点信息
 * @param level 节点层级
 * @param expandNodes 展开节点ID列表
 * @param includesBothEnd 是否需要包含开始、结束节点
 * @returns 当层每列节点信息
 */
function getLevelNodes(
  data: FlowsData,
  parent: null | GraphNode = null,
  level = 0,
  expandNodes: string[] = [],
  includesBothEnd = true,
) {
  const nodes: GraphNode[][] = [];
  const {
    gateways,
    activities,
    end_event: endNode,
    start_event: startNode,
    flows,
  } = data;
  // 当层节点映射
  const nodesMap: { [key: string]: FlowItem } = {
    ...gateways,
    ...activities,
    [startNode.id]: startNode,
    [endNode.id]: endNode,
  };
  let index = 0;

  // 处理开始节点
  nodes[index] = [];
  addNode(startNode, parent, nodes, index, level, expandNodes);

  const queue = [[startNode]];
  while (queue.length > 0) {
    // 同层同列节点
    const columnNodes = queue.shift();
    if (!columnNodes) break;
    const nextColumnNodes = [];
    index += 1;
    nodes[index] = [];
    for (const node of columnNodes) {
      if (node.outgoing) {
        const targets = Array.isArray(node.outgoing) ? node.outgoing : [node.outgoing];
        for (const targetId of targets) {
          const targetNode = nodesMap[flows[targetId].target];
          // 网关节点不处理
          const isGetewaysType = getewayTypes.includes(targetNode.type);
          !isGetewaysType && addNode(targetNode, parent, nodes, index, level, expandNodes);
          nextColumnNodes.push(targetNode);
        }
      }
    }
    // 去重，获取队列下次需要处理的节点
    const nextQueueValue = _.uniqBy(nextColumnNodes, 'id');
    nextQueueValue.length > 0 && queue.push(nextQueueValue);
  }

  return nodes.filter((nodes) => {
    // 为空则过滤掉
    if (nodes.length === 0) return false;

    if (includesBothEnd) return true;

    // 需要过滤掉开始、结束节点
    return !nodes.some(node => bothEndTypes.includes(node.data.type));
  });
}

/**
 * 获取节点的子节点
 * @param nodes 当层节点信息
 * @param expandNodes 展开节点ID列表
 */
function getNodeChildren(nodes: GraphNode[][], expandNodes: string[] = []) {
  for (const columnNodes of nodes) {
    for (const node of columnNodes) {
      const { data, level } = node;
      if (data.pipeline) {
        const childrenNodes = getLevelNodes(data.pipeline, node, level + 1, expandNodes, false);
        getNodeChildren(childrenNodes, expandNodes);
        node.children = childrenNodes;
      }
    }
  }
}

function initRootNodesX(nodes: GraphNode[][]) {
  const len = nodes.length;
  let preMaxEndX = 0; // 记录节点左侧的节点最大结束 x 位置
  for (let index = 0; index < len; index++) {
    const columnNodes = nodes[index];
    const x = (index === 0 ? preMaxEndX : config.horizontalSep + preMaxEndX);
    for (const node of columnNodes) {
      node.x = x + node.width / 2; // 渲染的时候x坐标是在width的一半位置
      preMaxEndX = Math.max(x + node.width, preMaxEndX);
    }
  }
}

/**
 * 计算节点位置
 * @param nodes 节点列表
 * @param expandNodes 展开节点ID列表
 * @param preMaxY 前一个节点递归的最大 y 值
 * @returns 当前节点递归的最大 y 值
 */
function calcNodesLocation(nodes: GraphNode[][], expandNodes: string[] = [], preMaxY = 0) {
  // 从后往前计算节点位置
  const reverseNodes = nodes.reverse();
  const len = reverseNodes.length;
  let maxY = preMaxY;
  for (let columnIndex = 0; columnIndex < len; columnIndex++) {
    const columnNodes = nodes[columnIndex]; // 获取同level的节点
    const coefficient = len - 1 - columnIndex; // 节点为倒叙
    for (const node of columnNodes) {
      const { level, index, parent, children, height } = node;
      let y = 0;
      if (index === 0 && level === 0) {
        y = 0; // 根节点第一行节点默认为0
      } else if (index === 0) {
        y = preMaxY + height + config.verticalSep;
      } else {
        const preNode = columnNodes[index - 1];
        const preNodeMaxY = getNodeDepthY([preNode]);
        y = config.verticalSep + height + preNodeMaxY;
      }
      node.y = y;
      if (parent && parent.x !== undefined) {
        const startX = config.chidlOffset + parent.x;
        node.x = startX + (node.width + config.horizontalSep) * coefficient;
      }
      maxY = Math.max(maxY, node.y);
      if (children && expandNodes.includes(node.id) && children.length > 0) {
        maxY = calcNodesLocation(children, expandNodes, maxY);
      }
    }
  }
  return maxY;
}

/**
 * 获取传入节点（若有子节点则为子节点）的最大 y 值
 * @param nodes 节点列表
 * @returns 递归节点中最大的 y 值
 */
function getNodeDepthY(nodes: GraphNode[]) {
  let maxY = 0;
  for (const node of nodes) {
    maxY = Math.max(maxY, node.y || 0);
    if (node.children && node.children.length > 0) {
      const flagNodes = node.children.reduce((nodes, item) => nodes.concat(item), []);
      const childMaxY = getNodeDepthY(flagNodes);
      maxY = Math.max(maxY, childMaxY);
    }
  }
  return maxY;
}

/**
 * 计算结束节点的 x 值
 * @param nodes 节点列表
 */
function calcEndNodeLocationX(nodes: GraphNode[]) {
  const customOffset = 185;
  const endNode = nodes.find(node => node.data.type === 'EmptyEndEvent');
  // x值为最大的节点信息
  const maxXNode = nodes.reduce((resNode, node) => {
    if (resNode.x !== undefined && node.x !== undefined && resNode.x > node.x) {
      return resNode;
    }
    return node;
  });
  if (endNode && maxXNode.x !== undefined) {
    endNode.x = maxXNode.level === 0 ? maxXNode.x : maxXNode.x + config.horizontalSep + customOffset;
  }
}
