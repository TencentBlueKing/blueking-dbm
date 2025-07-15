import _ from 'lodash';

import { FlowTypes, getTaskflowDetails } from '@services/source/taskflow';

import { random } from '@utils';

import { t } from '@locales/index';

export type FlowDetail = { type?: string } & ServiceReturnType<typeof getTaskflowDetails>;
export type FlowType = FlowDetail['end_event']['type'];

export type RenderKey = 'start_event' | 'end_event' | 'activities' | 'gateways';

export const getewayTypes: FlowType[] = [
  FlowTypes.ParallelGateway,
  FlowTypes.ConvergeGateway,
  FlowTypes.ConditionalParallelGateway,
];

export type Node = { collapsed: boolean; todoId: number } & FlowDetail['activities'][string];

export interface Edge {
  id: string;
  source: string;
  target: string;
}

export type TreeNode = {
  children?: TreeNode[];
  collapsed: boolean;
  id: string;
  name: string;
  parentProcessNodeId?: string;
  pipeline?: FlowDetail;
  status?: string;
  todoId: number;
  type: FlowType;
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

export function generateDifferentStatusTreeData(treeData: TreeNode[], status: string) {
  const filteredTreeData: TreeNode[] = [];
  treeData.forEach((item) => {
    if (
      (status === 'TODO' && (item.todoId || item.children?.find((child) => !!child.todoId))) ||
      item.status === status ||
      item.children?.find((child) => child.status === status)
    ) {
      const targetNode = _.cloneDeep(item);
      filteredTreeData.push(targetNode);
      if (targetNode.children) {
        Object.assign(targetNode, {
          children: generateDifferentStatusTreeData(targetNode.children!, status),
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
    Object.assign(item, {
      collapsed: false,
    });
    Object.assign(nodesMap, {
      [item.id]: true,
    });
  });
  const edges: Edge[] = [];
  totalEdges.forEach((edge) => {
    if ((nodesMap[edge.source] && nodesMap[edge.target]) || (data.id === edge.source && nodesMap[edge.target])) {
      edges.push(edge);
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
