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

import { FlowTypes, getTaskflowDetails } from '@services/source/taskflow';

import { t } from '@locales/index';

import { getNodeFilterStatus, type NodeFilterStatus } from './nodeStatus';

export type FlowDetail = { type?: string } & ServiceReturnType<typeof getTaskflowDetails>;

export type FlowType = FlowDetail['end_event']['type'];

/**
 * 接口里的原始节点。网关、开始、结束节点只有活动节点的部分字段，这里统一按活动节点的形状访问
 */
type RawNode = FlowDetail['activities'][string];

/**
 * 解析后的节点：原始字段 + 展示需要的派生字段，与接口返回的对象相互独立
 */
export type FlowNode = {
  isTaskRevoked: boolean;
  /** 所在子流程的嵌套深度，最外层为 0，CustomEdge 靠它识别跨层连线 */
  level: number;
  todoId: number;
} & RawNode;

export type TreeNode = {
  children?: TreeNode[];
} & FlowNode;

export interface Edge {
  id: string;
  source: string;
  target: string;
}

export interface FlowModel {
  /** 子流程节点、扇出网关 → 直属子节点 id，数组顺序即展示顺序 */
  childrenMap: Map<string, string[]>;
  /** 画布连线，两端都是可渲染的节点 id，已跨过 flow 中转与子流程首尾节点 */
  edges: Edge[];
  /** 全部层级的节点，key 为节点 id */
  nodeMap: Map<string, FlowNode>;
  /**
   * 所属子流程节点 id → 该层的全部节点 id，最外层的 key 为空串。
   * 与 childrenMap 的区别：这里按 pipeline 分层，扇出网关的分支节点仍算在网关所在的层里；
   * 布局要按层各跑一次，需要的是这个而不是 childrenMap
   */
  pipelineMap: Map<string, string[]>;
  /** 最外层节点 id，数组顺序即展示顺序，含开始与结束节点 */
  rootIds: string[];
}

export const getewayTypes: FlowType[] = [
  FlowTypes.ParallelGateway,
  FlowTypes.ConvergeGateway,
  FlowTypes.ConditionalParallelGateway,
];

// 扇出网关的 outgoing 是 flow id 数组，每条分支各自往下走，最终由汇聚网关收口
export const forkGatewayTypes: FlowType[] = [FlowTypes.ParallelGateway, FlowTypes.ConditionalParallelGateway];

// 网关与首尾节点接口不下发名称，按类型补展示名
const nodeTypeNameMap: Partial<Record<FlowType, string>> = {
  [FlowTypes.ConditionalParallelGateway]: t('条件网关'),
  [FlowTypes.ConvergeGateway]: t('汇聚网关'),
  [FlowTypes.EmptyEndEvent]: t('结束'),
  [FlowTypes.EmptyStartEvent]: t('开始'),
  [FlowTypes.ParallelGateway]: t('并行网关'),
};

// 只有流程还在运行或已失败时，待办才需要标记到节点上
function getTodoIdMap(data: FlowDetail) {
  const { status } = data.flow_info;
  if (status !== 'RUNNING' && status !== 'FAILED') {
    return {};
  }

  return (data.todos || []).reduce<Record<string, number>>((map, todoItem) => {
    if (todoItem.status === 'TODO') {
      Object.assign(map, { [todoItem.context.node_id]: todoItem.id });
    }
    return map;
  }, {});
}

/**
 * 解析任务流程接口数据
 *
 * 接口返回的是 bamboo-engine 的标准 pipeline tree：节点按 id 存放在 activities / gateways 里，连线单独放在
 * flows 里；节点的 outgoing 存的是 flow id，flows[flowId].target 才是下一个节点的 id；子流程以
 * activity.pipeline 的形式原样嵌套。
 *
 * 这里从开始节点沿 outgoing 走一遍，同时产出扁平节点表与层级关系，画布与搜索树都基于它派生。
 * 全程不修改接口返回的对象。
 */
export function parseFlow(data: FlowDetail): FlowModel {
  const nodeMap = new Map<string, FlowNode>();
  const childrenMap = new Map<string, string[]>();
  const pipelineMap = new Map<string, string[]>();
  const rootIds: string[] = [];
  const edges: Edge[] = [];

  const isTaskRevoked = data.flow_info.status === 'REVOKED';
  const todoIdMap = getTodoIdMap(data);

  const takeChildren = (id: string) => {
    const children: string[] = [];
    childrenMap.set(id, children);
    return children;
  };

  // 逐层解析，子流程各自递归。
  // level 用于区分最外层与子流程内部的首尾节点；entryNodeId 是所属子流程节点的 id，
  // 子流程内部的开始节点不渲染，它的出边改由子流程节点自己发出
  const parsePipeline = (pipeline: FlowDetail, level: number, rootSiblings: string[], entryNodeId: string) => {
    const ownIds: string[] = [];
    pipelineMap.set(entryNodeId, ownIds);
    const { activities, end_event: endEvent, flows, gateways, start_event: startEvent } = pipeline;
    const nodeLookup = {
      ...gateways,
      ...activities,
      [endEvent.id]: endEvent,
      [startEvent.id]: startEvent,
    } as Record<string, RawNode>;

    // 汇聚网关的入边到达次数，凑齐才能继续往下走
    const convergeArrivedMap: Record<string, number> = {};
    // 每遇到一个扇出网关压一次，对应的汇聚网关凑齐后弹出，回到网关所在的层级
    const siblingsStack: string[][] = [];

    // 子流程内部的开始与结束节点不参与展示，只保留最外层的
    const isHiddenNode = (type: FlowType) =>
      level > 0 && (type === FlowTypes.EmptyStartEvent || type === FlowTypes.EmptyEndEvent);

    const appendNode = (raw: RawNode, siblings: string[]) => {
      nodeMap.set(raw.id, {
        ...raw,
        isTaskRevoked,
        level,
        name: nodeTypeNameMap[raw.type] || raw.name,
        todoId: todoIdMap[raw.id] || 0,
      });
      siblings.push(raw.id);
      ownIds.push(raw.id);
    };

    const walkOutgoing = (fromId: string, outgoing: RawNode['outgoing'], siblings: string[]) => {
      const flowIds = Array.isArray(outgoing) ? outgoing : [outgoing];
      flowIds.forEach((flowId) => {
        const flow = flows[flowId];
        // 结束节点的 outgoing 是空字符串，取不到连线即为走到尽头
        if (!flow) {
          return;
        }
        const targetRaw = nodeLookup[flow.target];
        if (targetRaw && !isHiddenNode(targetRaw.type as FlowType)) {
          edges.push({ id: `${fromId}-${flow.target}`, source: fromId, target: flow.target });
        }
        walkNode(flow.target, siblings);
      });
    };

    const walkNode = (id: string, siblings: string[]) => {
      const raw = nodeLookup[id];
      // 正常流程里每个节点只会收录一次，重复即异常数据，跳过以免死循环。
      // 汇聚网关在凑齐入边之前不会入表，计数不受影响
      if (!raw || nodeMap.has(id)) {
        return;
      }

      const type = raw.type as FlowType;

      if (type === FlowTypes.ConvergeGateway) {
        const arrived = (convergeArrivedMap[id] || 0) + 1;
        convergeArrivedMap[id] = arrived;
        // 还有分支没走到，先挂起，由最后一条到达的分支继续
        if (arrived < raw.incoming.length) {
          return;
        }
        // 汇聚网关与它对应的扇出网关同级，排在并行块之后
        const forkSiblings = siblingsStack.pop() || siblings;
        appendNode(raw, forkSiblings);
        walkOutgoing(id, raw.outgoing, forkSiblings);
        return;
      }

      if (isHiddenNode(type)) {
        walkOutgoing(entryNodeId, raw.outgoing, siblings);
        return;
      }

      appendNode(raw, siblings);

      if (forkGatewayTypes.includes(type)) {
        // 各分支挂到网关名下，汇聚网关凭 siblingsStack 回到当前层级
        siblingsStack.push(siblings);
        walkOutgoing(id, raw.outgoing, takeChildren(id));
        return;
      }

      // SubProcess 也可能没有 pipeline，此时视为空子流程
      if (raw.pipeline) {
        parsePipeline(raw.pipeline, level + 1, takeChildren(id), id);
      }

      walkOutgoing(id, raw.outgoing, siblings);
    };

    walkNode(startEvent.id, rootSiblings);
  };

  parsePipeline(data, 0, rootIds, '');

  return { childrenMap, edges, nodeMap, pipelineMap, rootIds };
}

/**
 * 由解析结果生成搜索树数据
 */
export function buildTree(model: FlowModel) {
  const build = (ids: string[]) =>
    ids.reduce<TreeNode[]>((list, id) => {
      const node = model.nodeMap.get(id);
      if (node) {
        const childIds = model.childrenMap.get(id);
        // 树组件与状态统计都按 children 是否存在判定叶子节点，没有子节点时不能给空数组
        list.push(childIds?.length ? { ...node, children: build(childIds) } : { ...node });
      }
      return list;
    }, []);

  return build(model.rootIds);
}

export type NodeStatusCount = Record<'ALL' | NodeFilterStatus, number>;

/**
 * 按状态统计节点数量。
 *
 * 只统计叶子节点：子流程与扇出网关自身的状态由它下面的节点体现，一并计入会重复。
 * 顶部状态角标与搜索树的筛选下拉都用这一份，两处此前各写了一套遍历，口径已经对不上
 */
export function countNodeStatus(model: FlowModel) {
  const counts: NodeStatusCount = {
    ALL: 0,
    CREATED: 0,
    FAILED: 0,
    FINISHED: 0,
    READY: 0,
    RUNNING: 0,
    TODO: 0,
  };

  model.nodeMap.forEach((node, id) => {
    if (model.childrenMap.get(id)?.length || !node.status) {
      return;
    }
    counts.ALL += 1;
    counts[getNodeFilterStatus(node)] += 1;
  });

  return counts;
}

// 节点自身或它的任一子孙命中目标状态
function hasStatusInTree(node: TreeNode, status: string): boolean {
  if (getNodeFilterStatus(node) === status) {
    return true;
  }
  return (node.children || []).some((child) => hasStatusInTree(child, status));
}

export function generateDifferentStatusTreeData(treeData: TreeNode[], status: string) {
  const filteredTreeData: TreeNode[] = [];
  treeData.forEach((item) => {
    if (hasStatusInTree(item, status)) {
      // 只需要替换 children，浅拷贝即可，深拷贝会连整棵子流程原始数据一起复制
      const targetNode = { ...item };
      filteredTreeData.push(targetNode);
      if (targetNode.children) {
        targetNode.children = generateDifferentStatusTreeData(item.children!, status);
      }
    }
  });
  return filteredTreeData;
}
