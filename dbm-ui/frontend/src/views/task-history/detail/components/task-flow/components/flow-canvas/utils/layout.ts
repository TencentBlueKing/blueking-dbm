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

import { FlowTypes } from '@services/source/taskflow';

import { type FlowModel, type FlowNode, getewayTypes } from '@views/task-history/detail/utils';

import { AntVDagreLayout } from '@antv/g6';

/**
 * 画布节点：解析结果加上布局算出的位置。
 *
 * 搜索关键字与专家模式挂在每个节点上，而不是走模块级变量：自定义节点拿不到组件作用域，
 * 只有落到节点数据里，G6 的 setData 差异计算才能看到它们变了并触发重绘
 */
export type Node = {
  isExpand: boolean;
  isSuperUserMode: boolean;
  searchKey: string;
  style: {
    height: number;
    width: number;
    x: number;
    y: number;
  };
} & FlowNode;

/** 网关与首尾节点画成圆形，其余画成圆角矩形，尺寸与圆角都按它区分 */
export const roundFlowTypes = [FlowTypes.EmptyEndEvent, FlowTypes.EmptyStartEvent, ...getewayTypes];

const layoutConfig = {
  childOffset: 62, // 展开的子流程内容相对父节点的横向缩进，与节点标题的左缩进对齐
  horizontalSep: 40, // 列与列的间距
  verticalSep: 42, // 同一列内相邻节点的间距，取 3 的倍数让 dagre 的 nodesep 不出小数
};

/**
 * antv-dagre 的 nodesep / ranksep 不是节点间距，不能把目标值直接传进去。
 * 它先把两倍的值当 padding 加进节点尺寸（LR 下 ranksep 加宽、nodesep 加高），
 * 之后 nodesep 又原样交给内层 dagre 再生效一次，ranksep 则不往下传。
 * 实测的实际间距是纵向 3×nodesep、横向 2×ranksep，这里按目标间距反推真正该传的值
 */
const dagreSep = {
  nodesep: layoutConfig.verticalSep / 3,
  ranksep: layoutConfig.horizontalSep / 2,
};

/**
 * 节点尺寸的唯一来源。布局按它算间距、G6 按它渲染，两边必须取同一个值，
 * 否则算出来的间距和实际占位对不上
 */
export const getNodeSize = (node: Pick<FlowNode, 'pipeline' | 'type'>): [number, number] => {
  if (roundFlowTypes.includes(node.type)) {
    return [48, 48];
  }
  // 子流程节点左侧多留一段空档，放横跨在卡片左边框上的展开收起图标
  return node.pipeline ? [238, 48] : [224, 48];
};

/**
 * 扇出与汇聚的共用干线到网关的距离。布局按它给网关侧留净空，连线按它落干线，
 * 两边取同一个值，干线才不会压到展开出来的子内容上
 */
export const trunkGap = layoutConfig.horizontalSep / 2;

interface Placement {
  height: number;
  positions: Map<string, { x: number; y: number }>;
  width: number;
}

/**
 * 布局单个 pipeline 层，返回以该层内容左上角为原点的相对坐标，含所有已展开的下层节点。
 *
 * 骨架（列号与同列顺序）由 dagre 算出，喂进去的永远是折叠态的原始节点尺寸，与展开状态无关，
 * 所以反复展开收起不会让已有节点换位置。展开只做一件事：把子流程内容摆到父节点下方并缩进，
 * 再把这块内容的高度加到骨架里排在它后面的节点上。父节点自身、它上方的节点、以及所有节点的
 * x 都不会动，展开就是纯粹往下插入一段空间。
 */
async function layoutPipeline(ownerId: string, model: FlowModel, expandNodes: Set<string>): Promise<Placement> {
  const ids = model.pipelineMap.get(ownerId) || [];
  if (ids.length === 0) {
    return { height: 0, positions: new Map(), width: 0 };
  }

  // 先递归展开的子流程，拿到各自内容块的高度
  const childPlacements = new Map<string, Placement>();
  for (const id of ids) {
    if (expandNodes.has(id) && model.pipelineMap.has(id)) {
      childPlacements.set(id, await layoutPipeline(id, model, expandNodes));
    }
  }

  const idSet = new Set(ids);
  const localEdges = model.edges.filter((edge) => idSet.has(edge.source) && idSet.has(edge.target));
  const layout = new AntVDagreLayout();
  await layout.execute(
    {
      edges: localEdges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target })),
      nodes: ids.map((id) => ({ id })),
    },
    {
      // 默认的坐标分配会把节点在它的后继组里垂直居中：扇出网关会掉到分支扇形的正中间，
      // 网关前面的那串直链也跟着被推到中段，上方留出大片空白。
      // UL 取 Brandes-Köpf 的左上对齐，让节点跟第一个后继平齐，整体贴顶排
      align: 'UL',
      nodesep: dagreSep.nodesep,
      nodeSize: (node) => getNodeSize(model.nodeMap.get(node.id as string)!),
      rankdir: 'LR',
      ranksep: dagreSep.ranksep,
    },
  );

  // dagre 给的是节点中心，与 G6 的定位方式一致，直接留用
  const skeleton = new Map<string, { x: number; y: number }>();
  layout.forEachNode((node) => {
    skeleton.set(node.id as string, { x: node.x, y: node.y });
  });
  layout.destroy();

  // 每个节点所在的行往右占到哪一列为止：同一行的连线一路往右传递；连去别的行的边（分支汇进
  // 汇聚网关）要先在自己这一行横着走到目标跟前才拐弯，所以只算目标那一列，不再往后传。
  // 于是并行分支的行尾停在汇聚网关，主干行一路排到最后。
  // 按 x 从右往左算，同行的后继必定已经算好；同一行的节点取到的行尾一致，不会被拆开
  const rowReach = new Map<string, number>(ids.map((id) => [id, skeleton.get(id)!.x]));
  [...ids]
    .sort((a, b) => skeleton.get(b)!.x - skeleton.get(a)!.x)
    .forEach((id) => {
      const { x, y } = skeleton.get(id)!;
      const reach = localEdges.reduce((max, edge) => {
        if (edge.source !== id) {
          return max;
        }
        const target = skeleton.get(edge.target)!;
        return Math.max(max, target.y === y ? rowReach.get(edge.target)! : target.x);
      }, x);
      rowReach.set(id, reach);
    });

  // 每块展开内容会在它所在的纵向位置插入一段高度
  const expansions = ids
    .filter((id) => childPlacements.has(id))
    .map((id) => ({
      height: layoutConfig.verticalSep + childPlacements.get(id)!.height,
      id,
      x: skeleton.get(id)!.x,
      y: skeleton.get(id)!.y,
    }));

  // 同一行可能有多个节点各自展开，它们插入的高度落在同一个纵向位置上，彼此推不动对方，
  // 所以要按顺序自己往下摞开，否则几块内容会共用同一段空间叠在一起。
  // 次序按 x 从右往左：每块内容都从父节点左边缘往下引一条竖线，靠右的父节点引线 x 更大，
  // 压在靠左那块上方就会横穿它，所以让靠右的贴着父节点这一行，靠左的依次往下让
  const rowUsed = new Map<number, number>();
  const stackOffset = new Map<string, number>();
  [...expansions]
    .sort((a, b) => b.x - a.x)
    .forEach((item) => {
      const used = rowUsed.get(item.y) || 0;
      stackOffset.set(item.id, used);
      rowUsed.set(item.y, used + item.height);
    });

  // 展开内容从父节点这一列往右铺、往下压，只有正落在它下方的节点要让位。
  // 行尾停在展开点左边的行整个不在这块内容底下，比如并行分支之后才展开的节点，压不到分支上。
  // 同一行摞着的多块内容里，只要有一块压住自己，就得让开这块的底边，
  // 否则只让开自己那一块的高度，仍会被摞在它下面的内容盖住
  const shiftAt = (id: string) => {
    const reach = rowReach.get(id)!;
    const { y } = skeleton.get(id)!;
    const rowBottom = new Map<number, number>();
    expansions.forEach((item) => {
      if (item.y >= y || item.x > reach) {
        return;
      }
      rowBottom.set(item.y, Math.max(rowBottom.get(item.y) || 0, stackOffset.get(item.id)! + item.height));
    });
    return [...rowBottom.values()].reduce((sum, bottom) => sum + bottom, 0);
  };

  // 骨架按折叠尺寸算，不知道展开内容比父节点宽出来的那一段。会被这一段压住的只有汇聚干线：
  // 干线竖直跨越整组分支的行，而内容块正插在这些行之间。其余节点各占自己的行，内容块所在的
  // 行已被 shiftAt 腾空，碰不上，为它们让位纯属浪费横向空间。
  // 所以只给「本身是某组分支」的展开点让位，同列取最宽的一块，跨列累加：
  // 右边的列要让开左边每一列多出来的宽度
  const columnOverhang = new Map<number, number>();
  expansions.forEach((item) => {
    const underTrunk = localEdges.some(
      (edge) =>
        edge.source === item.id &&
        model.nodeMap.get(edge.target)!.type === FlowTypes.ConvergeGateway &&
        // 只有一条汇入的汇聚网关没有干线可画，不用为它让位
        localEdges.filter((other) => other.target === edge.target).length > 1,
    );
    if (!underTrunk) {
      return;
    }
    const [width] = getNodeSize(model.nodeMap.get(item.id)!);
    const overhang = layoutConfig.childOffset + childPlacements.get(item.id)!.width - width;
    columnOverhang.set(item.x, Math.max(columnOverhang.get(item.x) || 0, overhang, 0));
  });
  const pushAt = (x: number) =>
    [...columnOverhang].reduce((sum, [columnX, overhang]) => (columnX < x ? sum + overhang : sum), 0);

  const positions = new Map<string, { x: number; y: number }>();
  ids.forEach((id) => {
    const point = skeleton.get(id)!;
    const [width, height] = getNodeSize(model.nodeMap.get(id)!);
    const x = point.x + pushAt(point.x);
    const y = point.y + shiftAt(id);
    positions.set(id, { x, y });

    const child = childPlacements.get(id);
    if (child) {
      // 内容左上角对齐到父节点左边缘缩进处、下边缘之下，同行已有展开内容时再往下让开
      const originX = x - width / 2 + layoutConfig.childOffset;
      const originY = y + height / 2 + layoutConfig.verticalSep + stackOffset.get(id)!;
      child.positions.forEach((childPoint, childId) => {
        positions.set(childId, { x: originX + childPoint.x, y: originY + childPoint.y });
      });
    }
  });

  // 左上角用于归一化，宽高要回给父层做横向与纵向让位
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  positions.forEach((point, id) => {
    const [width, height] = getNodeSize(model.nodeMap.get(id)!);
    minX = Math.min(minX, point.x - width / 2);
    minY = Math.min(minY, point.y - height / 2);
    maxX = Math.max(maxX, point.x + width / 2);
    maxY = Math.max(maxY, point.y + height / 2);
  });

  // 归一化到左上角为原点，父层才能直接平移这块内容
  positions.forEach((point) => {
    Object.assign(point, { x: point.x - minX, y: point.y - minY });
  });

  return { height: maxY - minY, positions, width: maxX - minX };
}

/** 缓存的展开状态数上限，超过就淘汰最旧的一组，避免长时间停留在页面上时无限增长 */
const MAX_CACHED_LAYOUTS = 8;

export interface GraphDataOptions {
  expandNodes: Set<string>;
  isSuperUserMode: boolean;
  searchKey: string;
}

/**
 * 创建画布数据生成器。
 *
 * 布局只由拓扑与展开状态决定，节点状态怎么变都不影响坐标，所以两者不变时直接复用上次
 * 算好的位置。轮询每 10 秒来一次，变的只有状态，没有这层缓存每次都要把每一层的 dagre
 * 重跑一遍，大流程上就是肉眼可见的卡顿。
 * 生成器按画布实例创建，缓存不会在多个画布之间串
 */
export const createGraphDataBuilder = () => {
  const positionCache = new Map<string, Placement['positions']>();
  let topologyKey = '';

  return async (model: FlowModel, { expandNodes, isSuperUserMode, searchKey }: GraphDataOptions) => {
    // 子流程的 pipeline 可能在轮询过程中才下发，节点会变多，这时布局必须重算
    const nextTopologyKey = [...model.nodeMap.keys()].join(',');
    if (nextTopologyKey !== topologyKey) {
      topologyKey = nextTopologyKey;
      positionCache.clear();
    }

    const expandKey = [...expandNodes].sort().join(',');
    let positions = positionCache.get(expandKey);
    if (!positions) {
      ({ positions } = await layoutPipeline('', model, expandNodes));
      if (positionCache.size >= MAX_CACHED_LAYOUTS) {
        // Map 按插入顺序迭代，取第一个即最旧的一组。整表清掉的话，来回展开超过上限时
        // 连正要用的这一组也会被清走，下次再展回来又得重算
        positionCache.delete(positionCache.keys().next().value!);
      }
      positionCache.set(expandKey, positions);
    }

    const nodes: Node[] = [];
    positions.forEach((point, id) => {
      const node = model.nodeMap.get(id)!;
      const [width, height] = getNodeSize(node);
      nodes.push({
        ...node,
        isExpand: expandNodes.has(id),
        isSuperUserMode,
        searchKey,
        style: { height, width, x: point.x, y: point.y },
      });
    });

    return {
      // 端点坐标的校正由 CustomEdge.getEndpoints 负责，这里只筛可见性。
      // 同一份解析结果会随展开 / 折叠反复渲染，复制一份避免 G6 往边上挂内部状态污染模型
      edges: model.edges
        .filter((edge) => positions!.has(edge.source) && positions!.has(edge.target))
        .map((edge) => ({ ...edge })),
      nodes,
    };
  };
};
