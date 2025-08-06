import _ from 'lodash';

import { FlowTypes, getTaskflowDetails } from '@services/source/taskflow';

import { random } from '@utils';

import { t } from '@locales/index';

export type FlowDetail = { type?: string } & ServiceReturnType<typeof getTaskflowDetails>;
type FlowType = FlowDetail['end_event']['type'];

type FlowLine = FlowDetail['flows'][string];

// interface Node {
//   children?: Node[][];
//   data: Node;
//   id: string;
//   index: number;
//   isExpand: boolean;
//   level: number;
//   parent: null | Node;
//   style: {
//     height: number;
//     width: number;
//     x: number;
//     y: number;
//   };
// }

export const getewayTypes: FlowType[] = [
  FlowTypes.ParallelGateway,
  FlowTypes.ConvergeGateway,
  FlowTypes.ConditionalParallelGateway,
];

export type Node = {
  children?: Node[][];
  data: Node;
  id: string;
  index: number;
  isExpand: boolean;
  level: number;
  parent: null | Node;
  style: {
    height: number;
    width: number;
    x: number;
    y: number;
  };
  todoId: number;
} & FlowDetail['activities'][string];

export interface Edge {
  id: string;
  source: string;
  target: string;
}

export type TreeNode = {
  children?: TreeNode[];
  id: string;
  isExpand: boolean;
  name: string;
  parentProcessNodeId?: string;
  pipeline?: FlowDetail;
  status?: string;
  todoId: number;
  type: FlowType;
};

const bothEndTypes: FlowType[] = [FlowTypes.EmptyStartEvent, FlowTypes.EmptyEndEvent];

const roundTypes: FlowType[] = [
  FlowTypes.EmptyStartEvent,
  FlowTypes.EmptyEndEvent,
  FlowTypes.ParallelGateway,
  FlowTypes.ConvergeGateway,
  FlowTypes.ConditionalParallelGateway,
];

const layoutConfig = {
  chidlOffset: 66, // 子节点 x 偏移量
  horizontalSep: 40, // 节点水平间距
  verticalSep: 56, // 节点垂直间距
};

const nodeTypeNameMap = {
  [FlowTypes.ConditionalParallelGateway]: t('条件网关'),
  [FlowTypes.ConvergeGateway]: t('汇聚网关'),
  [FlowTypes.EmptyEndEvent]: t('结束'),
  [FlowTypes.EmptyStartEvent]: t('开始'),
  [FlowTypes.ParallelGateway]: t('并行网关'),
};
const resetNameTypes = Object.keys(nodeTypeNameMap);

function getTodoNodeIdList(details: FlowDetail) {
  const { status } = details.flow_info;
  return (details.todos || []).reduce<
    {
      nodeId: string;
      todoId: number;
    }[]
  >((prevList, todoItem) => {
    if ((status === 'RUNNING' || status === 'FAILED') && todoItem.status === 'TODO') {
      prevList.push({
        nodeId: todoItem.context.node_id,
        todoId: todoItem.id,
      });
    }
    return prevList;
  }, []);
}

export function generateCommonData(data: FlowDetail) {
  const nodes: Node[] = [];
  // 存在子流程的时候，子流程的起点对应与父级节点id的映射，包含最外层的结束节点
  const pipelineNodeToStartEventMap: Record<string, string> = {};
  const outerStartEndEventIdMap = {
    [data.end_event.id]: true,
    [data.start_event.id]: true,
  };
  const todoNodeList = getTodoNodeIdList(data);
  const nodeIdTodoIdMap = todoNodeList.reduce<Record<string, number>>(
    (map, item) =>
      Object.assign(map, {
        [item.nodeId]: item.todoId,
      }),
    {},
  );

  const traverse = (list: any[] = []) => {
    list.forEach((item) => {
      if (resetNameTypes.includes(item.type)) {
        Object.assign(item, { name: nodeTypeNameMap[item.type as keyof typeof nodeTypeNameMap] });
      }
      Object.assign(item, { todoId: nodeIdTodoIdMap[item.id] || 0 });
      nodes.push(item);
      if (item.pipeline) {
        pipelineNodeToStartEventMap[item.id] = item.pipeline.start_event.id;
        pipelineNodeToStartEventMap[item.pipeline.start_event.id] = item.id;
        const { activities, gateways } = item.pipeline;
        traverse([...Object.values(activities), ...Object.values(gateways), startEvent, endEvent]);
      }
    });
    return list;
  };

  const { activities, end_event: endEvent, gateways, start_event: startEvent } = data;

  traverse([...Object.values(activities), ...Object.values(gateways), startEvent, endEvent]);
  const nodesMap = _.keyBy(nodes, 'id');
  return { nodes, nodesMap, outerStartEndEventIdMap, pipelineNodeToStartEventMap, todoNodeList };
}

// 判断当前节点的所有子孙节点中是否存在相同的状态
function isExistSameStatusInDeepChildren(node: TreeNode, status: string): boolean {
  if (status === 'TODO' && node.todoId > 0) {
    return true;
  }
  if (node.status === status) {
    return true;
  }
  if (node.children) {
    return node.children.some((child) => isExistSameStatusInDeepChildren(child, status));
  }
  return false;
}

export function generateDifferentStatusTreeData(treeData: TreeNode[], status: string) {
  const filteredTreeData: TreeNode[] = [];
  treeData.forEach((item) => {
    if (
      (status === 'TODO' && (item.todoId || item.children?.find((child) => !!child.todoId))) ||
      item.status === status ||
      isExistSameStatusInDeepChildren(item, status)
    ) {
      const targetNode = _.cloneDeep(item);
      filteredTreeData.push(targetNode);
      if (targetNode.children) {
        Object.assign(targetNode, {
          children: generateDifferentStatusTreeData(item.children!, status),
        });
      }
    }
  });
  return filteredTreeData;
}

export function generateTreeData(
  baseData: FlowDetail,
  nodesMap: Record<string, Node>,
  edgesMap: Record<string, Set<string>>,
  parentProcessNodeId = '',
) {
  const { start_event: startEvent } = baseData;
  const treeData: TreeNode[] = [];
  let currentNode = nodesMap[Array.from(edgesMap[startEvent.id])[0]] as any;

  while (currentNode && currentNode.type !== 'EmptyEndEvent') {
    if (parentProcessNodeId) {
      currentNode.parentProcessNodeId = parentProcessNodeId;
    }
    treeData.push(currentNode);
    if (currentNode.pipeline) {
      currentNode.children = generateTreeData(currentNode.pipeline, nodesMap, edgesMap, currentNode.id);
    }
    const nextNodeIds = Array.from(edgesMap[currentNode.id]);
    if (nextNodeIds.length > 1) {
      // 一 对 多的网关节点
      currentNode.children = [];
      nextNodeIds.forEach((nextNodeId) => {
        const nextNode = nodesMap[nextNodeId] as any;
        if (parentProcessNodeId) {
          Object.assign(nextNode, { parentProcessNodeId });
        }
        if (nextNode.pipeline) {
          nextNode.children = generateTreeData(nextNode.pipeline, nodesMap, edgesMap, nextNode.id);
        }
        currentNode.children.push(nextNode);
      });
      const nextNode = nodesMap[Array.from(edgesMap[nodesMap[nextNodeIds[0]].id])[0]];
      currentNode = nextNode;
    } else {
      currentNode = nodesMap[nextNodeIds[0]];
    }
  }
  return treeData;
}

export function generateEdges(
  baseData: FlowDetail,
  allNodes: Node[],
  pipelineNodeToStartEventMap: Record<string, string>,
  outerStartEndEventIdMap: Record<string, boolean>,
) {
  const calcSourceNode = (id: string, data: FlowDetail) => {
    if (data.activities[id] || data.gateways[id] || data.end_event.id === id) {
      // 直接命中节点
      return id;
    }
    if (data.start_event.id === id) {
      // 命中开始节点
      if (outerStartEndEventIdMap[id]) {
        // 最外层开始节点
        return id;
      }
      return id;
    }

    if (data.flows[id]) {
      // 命中flow，可能要反复跳转到gateway或者其他flow直至节点id
      const sourceId = data.flows[id].source;
      return calcSourceNode(sourceId, data);
    }
  };

  const calcTargetNode = (id: string, data: FlowDetail) => {
    if (data.activities[id] || data.gateways[id] || data.start_event.id === id) {
      // 直接命中节点
      return id;
    }

    if (data.end_event.id === id) {
      // 命中结束节点
      if (outerStartEndEventIdMap[id]) {
        // 最外层结束节点
        return id;
      }
      return id;
    }

    if (data.flows[id]) {
      // 命中flow，可能要反复跳转到gateway或者其他flow直至节点id
      const targetId = data.flows[id].target;
      return calcTargetNode(targetId, data);
    }
  };
  const edgesMap: Record<string, Set<string>> = {};
  const traverse = (data: FlowDetail) => {
    if (Object.keys(data.flows).length) {
      const flowValueList = Object.values(data.flows);
      flowValueList.forEach((item) => {
        const sourceIdOrList = calcSourceNode(item.source, data);
        const targetIdOrList = calcTargetNode(item.target, data);

        if (!sourceIdOrList || !targetIdOrList) {
          return;
        }
        const sourceList = Array.isArray(sourceIdOrList) ? _.flatMapDeep(sourceIdOrList) : [sourceIdOrList];
        const targetList = Array.isArray(targetIdOrList) ? _.flatMapDeep(targetIdOrList) : [targetIdOrList];
        if (sourceList.length && targetList.length) {
          sourceList.forEach((source) => {
            targetList.forEach((target) => {
              if (!target) {
                return;
              }
              if (edgesMap[source]) {
                edgesMap[source].add(target);
              } else {
                Object.assign(edgesMap, {
                  [source]: new Set([target]),
                });
              }
            });
          });
          return;
        }
      });
    }
    Object.values(data.activities).forEach((activity) => {
      if (activity.pipeline) {
        traverse(activity.pipeline);
      }
    });
  };
  traverse(baseData);
  const edges: Edge[] = [];
  Object.entries(edgesMap).forEach(([source, targetSet]) => {
    targetSet?.forEach((target) => {
      edges.push({
        id: random(),
        source,
        target,
      });
    });
  });
  Object.entries(pipelineNodeToStartEventMap).forEach(([source, target]) => {
    edges.push({
      id: random(),
      source,
      target,
    });
  });
  allNodes.forEach((node) => {
    if (node.pipeline) {
      // 由于画布子流程需要去掉开始和结束节点，子流程需要新增一条直接指向开始节点之后的节点的边
      const startNodeId = pipelineNodeToStartEventMap[node.id];
      const firstNodeId = Array.from(edgesMap[startNodeId])[0];
      edges.push({
        id: random(),
        source: node.id,
        target: firstNodeId,
      });
    }
  });
  // edges的范围比edgesMap要大
  return { edges, edgesMap };
}

export function getCurrentNodeChildenDataAndEdges(data: FlowDetail, totalEdges: Edge[], isOuter = false) {
  const nodes = [...Object.values(data.activities), ...Object.values(data.gateways)] as Node[];
  if (isOuter) {
    nodes.push(data.start_event as Node, data.end_event as Node);
  }
  const nodesMap: Record<string, boolean> = {};
  nodes.forEach((item) => {
    Object.assign(nodesMap, {
      [item.id]: true,
    });
  });
  const edges: Edge[] = [];
  totalEdges.forEach((edge) => {
    if (nodesMap[edge.source] && nodesMap[edge.target]) {
      edges.push(edge);
    } else if (data.id === edge.source && nodesMap[edge.target]) {
      edges.push(edge);
      const subProcessStartChildNode = nodes.find((node) => node.id === edge.target)!;
      Object.assign(subProcessStartChildNode, {
        isStartNodeOfSubProcess: true,
      });
    }
  });
  return {
    edges,
    nodes,
  };
}

export function getRemoveCollapsedData(
  collapsedMap: Record<
    string,
    {
      edges: Edge[];
      nodes: Node[];
    }
  >,
  removeNodeId: string,
) {
  const dataMap = collapsedMap;
  const { edges, nodes } = collapsedMap[removeNodeId];
  delete dataMap[removeNodeId];
  const totalEdges = _.cloneDeep(edges);
  const totalNodes = _.cloneDeep(nodes);
  const findRelatedNodeData = (nodeList: Node[]) => {
    nodeList.forEach((node) => {
      if (collapsedMap[node.id]) {
        const { edges, nodes } = collapsedMap[node.id];
        delete dataMap[node.id];
        totalEdges.push(...edges);
        totalNodes.push(...nodes);
        findRelatedNodeData(nodes);
      }
    });
  };
  findRelatedNodeData(totalNodes);
  return {
    edges: totalEdges,
    nodes: totalNodes,
  };
}

/**
 * 格式化节点数据
 */
export const formatGraphData = (data: FlowDetail, expandNodes: Set<string> = new Set()) => {
  const rootNodes = getLevelNodes(data, null, 0, expandNodes); // 所有根节点
  const bothEndNodes = []; // 开始、结束根节点
  const roots = []; // 非开始、结束的根节点
  // 分离开始、结束根节点
  for (const nodes of rootNodes) {
    if (nodes.some((node) => bothEndTypes.includes(node.data.type))) {
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
  const flagNodes: Node[] = [];
  getFlagNodes(rootNodes, flagNodes, expandNodes);
  // 计算结束节点 x 值
  calcEndNodeLocationX(flagNodes);
  const availableNodes: Node[] = [];
  const nodesCountMap: Record<string, number> = {};
  flagNodes.forEach((node) => {
    nodesCountMap[node.id] = nodesCountMap[node.id] ? nodesCountMap[node.id] + 1 : 1;
    if (nodesCountMap[node.id] === 1) {
      availableNodes.push(node);
    }
  });

  // 处理连线坐标
  const lines = formartLines(data);
  const renderLines = getRenderLines(lines, availableNodes);

  return {
    lines: renderLines,
    locations: availableNodes,
  };
};

/**
 * 查询目标节点
 */
function findTargetNode(id: string, nodes: Node[]) {
  return nodes.find((node) => node.id === id);
}

function getRenderLines(lines: Edge[], nodes: Node[]) {
  const renderLines: Edge[] = [];
  for (const line of lines) {
    const newLine = _.cloneDeep(line);
    const { source, target } = newLine;
    const sourceNode = findTargetNode(source, nodes);
    const targetNode = findTargetNode(target, nodes);

    if (sourceNode && targetNode) {
      const isLowerLevel = sourceNode.level !== targetNode.level; // 节点不属于同一层
      const { width: sourceWidth, x: sourceX = 0, y: sourceY = 0 } = sourceNode.style;
      const { height: targetHeight, width: targetWidth, x: targetX = 0, y: targetY = 0 } = targetNode.style;
      const targetData = targetNode.data;
      const sourceOffsetX = sourceWidth / 2 - 14 - 24;
      const targetOffsetX = targetWidth / 2;
      const isParallelGateway = targetData.type === FlowTypes.ParallelGateway;
      Object.assign(source, {
        x: isLowerLevel ? sourceX - sourceOffsetX : sourceX,
        y: sourceY,
      });
      Object.assign(target, {
        x: isLowerLevel ? (isParallelGateway ? targetX : targetX - targetOffsetX) : targetX,
        y: isLowerLevel ? (isParallelGateway ? targetY : targetY + targetHeight / 2) : targetY,
      });
      renderLines.push(newLine);
    }
  }
  return renderLines;
}

const getLineTargets = (
  node: FlowDetail['activities'][number],
  nodeMap: { [key: string]: FlowDetail },
  flows: { [key: string]: FlowLine },
  isCurrent = false,
  targets: string[] = [],
  isStartNode = false,
): string[] => {
  const { id, outgoing, type } = node;
  // 返回当前节点
  if (isCurrent && !getewayTypes.includes(type)) {
    targets.push(node.id);
    return targets;
  }

  if (outgoing === '') {
    return targets;
  }

  if (isStartNode && type === FlowTypes.ParallelGateway) {
    return [id];
  }

  if (Array.isArray(outgoing)) {
    outgoing.forEach((id: string) => {
      getLineTargets(nodeMap[flows[id].target] as any, nodeMap, flows, true, targets, isStartNode);
    });

    return targets;
  }

  const targetNode = nodeMap[flows[outgoing].target];
  if (getewayTypes.includes(targetNode.type as FlowType)) {
    targets.push(targetNode.id);
    return targets;
  }

  targets.push(targetNode.id);
  return targets;
};

/**
 * 格式化画布连线
 */
const formartLines = (data: FlowDetail, level = 0, lines: Edge[] = []) => {
  const { activities, end_event: endNode, flows, gateways, start_event: startNode } = data;
  // 当层节点映射
  const nodesMap = {
    ...gateways,
    ...activities,
    [endNode.id]: endNode,
    [startNode.id]: startNode,
  } as Record<string, FlowDetail['activities'][number]>;
  const linesMap: { [nodeId: string]: string } = {};
  for (const flowLine of Object.values(flows)) {
    linesMap[flowLine.source] = flowLine.id;
  }
  for (const node of Object.values(nodesMap)) {
    if (node.type === FlowTypes.EmptyEndEvent && level > 0) {
      continue;
    }

    // 处理子流程 start 节点
    if (node.type === FlowTypes.EmptyStartEvent && level > 0) {
      const { outgoing } = node;
      const addLine = (lineId: string) => {
        const { target } = flows[lineId];
        const targets = getLineTargets(nodesMap[target] as any, nodesMap as any, flows, true, [], true);
        for (const id of targets) {
          lines.push({
            id: `${data.id}-${id}`,
            source: data.id,
            target: id,
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

    const targets = getLineTargets(node, nodesMap as any, flows);
    for (const id of targets) {
      lines.push({
        id: `${node.id}-${id}`,
        source: node.id,
        target: id,
      });
    }

    if (node.pipeline) {
      formartLines(node.pipeline, level + 1, lines);
    }
  }

  return lines;
};

/**
 * 获取扁平化节点列表
 */
function getFlagNodes(nodes: Node[][], flagNodes: Node[] = [], expandNodes: Set<string> = new Set()) {
  for (const columnNodes of nodes) {
    for (const node of columnNodes) {
      flagNodes.push(node);

      if (node.children && expandNodes.has(node.id) && node.children.length > 0) {
        getFlagNodes(node.children, flagNodes, expandNodes);
      }
    }
  }
}

/**
 * 添加节点到当前层级的列中
 */
function addNode(
  node: FlowDetail,
  parent: null | Node = null,
  nodes: Node[][],
  index: number,
  level: number,
  expandNodes: Set<string> = new Set(),
) {
  const isRoundType = roundTypes.includes(node.type as FlowTypes);
  const len = nodes[index].length;
  const Node = {
    ...node,
    data: node,
    id: node.id,
    index: len,
    isExpand: expandNodes.has(node.id),
    level,
    parent,
    style: {
      height: 48,
      width: isRoundType ? 48 : 240,
    },

    type: node.type,
  } as unknown as Node;
  nodes[index].push(Node);
}

/**
 * 获取当层每列节点信息
 */
function getLevelNodes(
  data: FlowDetail,
  parent: null | Node = null,
  level = 0,
  expandNodes: Set<string> = new Set(),
  includesBothEnd = true,
) {
  const nodes: Node[][] = [];
  const { activities = {}, end_event: endNode, flows, gateways = {}, start_event: startNode } = data;
  // 当层节点映射
  const nodesMap = {
    ...gateways,
    ...activities,
    [endNode.id]: endNode,
    [startNode.id]: startNode,
  };
  let index = 0;
  // 处理开始节点
  nodes[index] = [];
  addNode(startNode as any, parent, nodes, index, level, expandNodes);
  const queue = [[startNode]];
  while (queue.length > 0) {
    // 同层同列节点
    const columnNodes = queue.shift();

    if (!columnNodes) {
      break;
    }
    const nextColumnNodes = [];
    index += 1;
    nodes[index] = [];
    for (const node of columnNodes) {
      if (node.outgoing) {
        const targets = Array.isArray(node.outgoing) ? node.outgoing : [node.outgoing];
        for (const targetId of targets) {
          const targetNode = nodesMap[flows[targetId].target];
          addNode(targetNode as any, parent, nodes, index, level, expandNodes);
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
    if (nodes.length === 0) {
      return false;
    }

    if (includesBothEnd) {
      return true;
    }

    // 需要过滤掉开始、结束节点
    return !nodes.some((node) => bothEndTypes.includes(node.data.type));
  });
}

/**
 * 获取节点的子节点
 */
function getNodeChildren(nodes: Node[][], expandNodes: Set<string> = new Set()) {
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

function initRootNodesX(nodes: Node[][]) {
  const len = nodes.length;
  let preMaxEndX = 0; // 记录节点左侧的节点最大结束 x 位置
  for (let index = 0; index < len; index++) {
    const columnNodes = nodes[index];
    const x = index === 0 ? preMaxEndX : layoutConfig.horizontalSep + preMaxEndX;
    for (const node of columnNodes) {
      node.style.x = x + node.style.width / 2; // 渲染的时候x坐标是在width的一半位置
      preMaxEndX = Math.max(x + node.style.width, preMaxEndX);
    }
  }
}

/**
 * 计算节点位置
 */
function calcNodesLocation(nodes: Node[][], expandNodes: Set<string> = new Set(), preMaxY = 0) {
  // 从后往前计算节点位置
  const reverseNodes = nodes.reverse();
  const tmpNodes = _.cloneDeep(nodes).reverse();
  const len = reverseNodes.length;
  let maxY = preMaxY;
  for (let columnIndex = 0; columnIndex < len; columnIndex++) {
    const columnNodes = nodes[columnIndex]; // 获取同level的节点
    const coefficient = len - 1 - columnIndex; // 节点为倒叙，就是同层节点列表的下标
    for (const node of columnNodes) {
      const { children, index, level, parent } = node;
      const height = node.style.height;
      let y = 0;
      if (index === 0 && level === 0) {
        y = 0; // 根节点第一行节点默认为0
      } else if (index === 0) {
        y = preMaxY + height + layoutConfig.verticalSep;
      } else {
        const preNode = columnNodes[index - 1];
        const preNodeMaxY = getNodeDepthY([preNode]);
        y = layoutConfig.verticalSep + height + preNodeMaxY;
      }
      node.style.y = y;
      if (parent?.style.x !== undefined) {
        // ??
        const startX = layoutConfig.chidlOffset + parent.style.x;
        const currentX = tmpNodes
          .slice(0, coefficient)
          .reduce((sum, nodeList) => sum + nodeList[0].style.width + layoutConfig.horizontalSep, startX);
        node.style.x = currentX;
        // 纠正网关节点布局
        if (getewayTypes.includes(node.data.type)) {
          node.style.x = currentX - 88;
        }
        // node.style.x = startX + (node.style.width + layoutConfig.horizontalSep) * coefficient;
      }
      maxY = Math.max(maxY, node.style.y);
      if (children && expandNodes.has(node.id) && children.length > 0) {
        maxY = calcNodesLocation(children, expandNodes, maxY);
      }
    }
  }
  return maxY;
}

/**
 * 获取传入节点（若有子节点则为子节点）的最大 y 值
 */
function getNodeDepthY(nodes: Node[]) {
  let maxY = 0;
  for (const node of nodes) {
    maxY = Math.max(maxY, node.style?.y || 0);
    if (node.children && node.children.length > 0) {
      const flagNodes = node.children.reduce((nodes, item) => nodes.concat(item as any), []);
      const childMaxY = getNodeDepthY(flagNodes);
      maxY = Math.max(maxY, childMaxY);
    }
  }
  return maxY;
}

/**
 * 计算结束节点的 x 值
 */
function calcEndNodeLocationX(nodes: Node[]) {
  const customOffset = 185;
  const endNode = nodes.find((node) => node.data.type === 'EmptyEndEvent');
  // x值为最大的节点信息
  const maxXNode = nodes.reduce((resNode, node) => {
    if (resNode.style.x !== undefined && node.style.x !== undefined && resNode.style.x > node.style.x) {
      return resNode;
    }
    return node;
  });
  if (endNode && maxXNode.style.x !== undefined) {
    endNode.style.x =
      maxXNode.level === 0 ? maxXNode.style.x : maxXNode.style.x + layoutConfig.horizontalSep + customOffset;
  }
}
