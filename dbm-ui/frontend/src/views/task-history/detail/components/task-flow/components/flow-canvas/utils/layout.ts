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

import { type FlowModel, type FlowNode, forkGatewayTypes, getewayTypes } from '@views/task-history/detail/utils';

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

/** 单个 pipeline 层的骨架，只由拓扑决定，与展开状态无关 */
interface Skeleton {
  /** 节点中心坐标，已做过汇聚网关提顶 */
  points: Map<string, { x: number; y: number }>;
  /** 每个节点所在的行往右占到哪一列为止 */
  rowReach: Map<string, number>;
  /** 每个节点所在的行从哪一列开始 */
  rowStart: Map<string, number>;
  /** 跨行连线的竖直干线：所在列与竖直跨过的行区间 */
  trunks: { bottom: number; column: number; top: number }[];
}

/**
 * 算出单个 pipeline 层的骨架（列号与同列顺序）。
 *
 * 喂给 dagre 的永远是折叠态的原始节点尺寸，与展开状态无关，所以反复展开收起不会让已有节点换位置，
 * 同一层的骨架也可以在不同展开状态之间复用
 */
async function buildSkeleton(ids: string[], model: FlowModel): Promise<Skeleton> {
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
      // UL 取 Brandes-Köpf 的左上对齐，让节点跟第一个后继平齐，整体贴顶排。
      // 汇聚网关对齐的是前驱中位数，仍会居中，布局完再单独提到顶部
      align: 'UL',
      nodesep: dagreSep.nodesep,
      nodeSize: (node) => getNodeSize(model.nodeMap.get(node.id as string)!),
      rankdir: 'LR',
      ranksep: dagreSep.ranksep,
    },
  );

  // dagre 给的是节点中心，与 G6 的定位方式一致，直接留用
  const points = new Map<string, { x: number; y: number }>();
  layout.forEachNode((node) => {
    points.set(node.id as string, { x: node.x, y: node.y });
  });
  layout.destroy();

  // 每个节点的入边源节点与出边目标节点，保持 model.edges 里的顺序
  const sourcesMap = new Map<string, string[]>(ids.map((id) => [id, []]));
  const targetsMap = new Map<string, string[]>(ids.map((id) => [id, []]));
  localEdges.forEach((edge) => {
    sourcesMap.get(edge.target)!.push(edge.source);
    targetsMap.get(edge.source)!.push(edge.target);
  });

  // 边总是从左列连向右列，下面几步都按列序逐个传递。汇聚网关提顶只改 y，x 的次序排一次即可
  const idsByX = [...ids].sort((a, b) => points.get(a)!.x - points.get(b)!.x);

  // UL 让节点对齐前驱的中位数，汇聚网关有三条及以上分支时会落到中间那条，后面的主干跟着下沉。
  // 这里把汇聚网关提到最上面那条分支的高度，与扇出网关贴顶一致；其余节点跟着入边的源节点移同样的距离，
  // 下游整体上移，dagre 排好的相对位置不变。除汇聚网关外节点只有一条入边。
  // 按 x 从左往右算，源节点必定已经算好
  const alignOffset = new Map<string, number>();
  idsByX.forEach((id) => {
    const point = points.get(id)!;
    const sources = sourcesMap.get(id)!;
    if (sources.length === 0) {
      alignOffset.set(id, 0);
      return;
    }
    if (model.nodeMap.get(id)!.type === FlowTypes.ConvergeGateway) {
      const top = Math.min(...sources.map((source) => points.get(source)!.y));
      alignOffset.set(id, top - point.y);
      point.y = top;
      return;
    }
    const offset = alignOffset.get(sources[0])!;
    alignOffset.set(id, offset);
    point.y += offset;
  });

  // 每个节点所在的行往右占到哪一列为止：同一行的连线一路往右传递；连去别的行的边（分支汇进
  // 汇聚网关）要先在自己这一行横着走到目标跟前才拐弯，所以只算目标那一列，不再往后传。
  // 于是并行分支的行尾停在汇聚网关，主干行一路排到最后。
  // 按 x 从右往左算，同行的后继必定已经算好；同一行的节点取到的行尾一致，不会被拆开
  const rowReach = new Map<string, number>(ids.map((id) => [id, points.get(id)!.x]));
  [...idsByX].reverse().forEach((id) => {
    const { x, y } = points.get(id)!;
    const reach = targetsMap.get(id)!.reduce((max, targetId) => {
      const target = points.get(targetId)!;
      return Math.max(max, target.y === y ? rowReach.get(targetId)! : target.x);
    }, x);
    rowReach.set(id, reach);
  });

  // 每个节点所在的行从哪一列开始：沿同一行的入边往左传，与 rowReach 一起圈出这一行横跨的范围
  const rowStart = new Map<string, number>(ids.map((id) => [id, points.get(id)!.x]));
  idsByX.forEach((id) => {
    const { y } = points.get(id)!;
    sourcesMap.get(id)!.forEach((sourceId) => {
      if (points.get(sourceId)!.y === y) {
        rowStart.set(id, Math.min(rowStart.get(id)!, rowStart.get(sourceId)!));
      }
    });
  });

  // 跨行的边都有一段竖直干线，同一行的边是一条直线，没有干线。
  // 干线只有汇聚边贴在目标那一侧，扇出边与普通跨行边都落在源节点这一侧（见 CustomEdge.getKeyPath）。
  // 记下每条干线所在的列，以及它竖直跨过的行区间
  const trunks: Skeleton['trunks'] = [];
  localEdges.forEach((edge) => {
    const source = points.get(edge.source)!;
    const target = points.get(edge.target)!;
    if (source.y === target.y) {
      return;
    }
    const isConverge =
      !forkGatewayTypes.includes(model.nodeMap.get(edge.source)!.type) &&
      model.nodeMap.get(edge.target)!.type === FlowTypes.ConvergeGateway;
    trunks.push({
      bottom: Math.max(source.y, target.y),
      column: isConverge ? target.x : source.x,
      top: Math.min(source.y, target.y),
    });
  });

  return { points, rowReach, rowStart, trunks };
}

/**
 * 布局单个 pipeline 层，返回以该层内容左上角为原点的相对坐标，含所有已展开的下层节点。
 *
 * 骨架由 buildSkeleton 给出，按层缓存在 skeletonCache 里。展开只做一件事：把子流程内容摆到父节点下方并缩进，
 * 再把这块内容的高度加到骨架里排在它后面的节点上。父节点自身、它上方的节点、以及所有节点的
 * x 都不会动，展开就是纯粹往下插入一段空间。
 */
async function layoutPipeline(
  ownerId: string,
  model: FlowModel,
  expandNodes: Set<string>,
  skeletonCache: Map<string, Skeleton>,
): Promise<Placement> {
  const ids = model.pipelineMap.get(ownerId) || [];
  if (ids.length === 0) {
    return { height: 0, positions: new Map(), width: 0 };
  }

  // 先递归展开的子流程，拿到各自内容块的高度
  const childPlacements = new Map<string, Placement>();
  for (const id of ids) {
    if (expandNodes.has(id) && model.pipelineMap.has(id)) {
      childPlacements.set(id, await layoutPipeline(id, model, expandNodes, skeletonCache));
    }
  }

  let skeleton = skeletonCache.get(ownerId);
  if (!skeleton) {
    skeleton = await buildSkeleton(ids, model);
    skeletonCache.set(ownerId, skeleton);
  }
  const { points, rowReach, rowStart, trunks } = skeleton;

  // 每块展开内容会在它所在的纵向位置插入一段高度，横向从父节点左边缘占到内容右边缘
  const expansions = ids
    .filter((id) => childPlacements.has(id))
    .map((id) => {
      const { x, y } = points.get(id)!;
      const [width] = getNodeSize(model.nodeMap.get(id)!);
      const left = x - width / 2;
      return {
        height: layoutConfig.verticalSep + childPlacements.get(id)!.height,
        id,
        left,
        right: left + layoutConfig.childOffset + childPlacements.get(id)!.width,
        x,
        y,
      };
    });

  // 同一行可能有多个节点各自展开，它们插入的高度落在同一个纵向位置上，彼此推不动对方，
  // 横向范围挨得比列间距还近的就要自己往下摞开，否则几块内容会叠在一起；离得够远的各自贴着父节点。
  // 次序按 x 从右往左：每块内容都从父节点左边缘往下引一条竖线，靠右的父节点引线 x 更大，
  // 压在靠左那块上方就会横穿它，所以让靠右的贴着父节点这一行，靠左的依次往下让
  const stackOffset = new Map<string, number>();
  const stackOrder = [...expansions].sort((a, b) => b.x - a.x);
  stackOrder.forEach((item, index) => {
    const offset = stackOrder.slice(0, index).reduce((max, other) => {
      const isOverlap =
        other.y === item.y &&
        item.left < other.right + layoutConfig.horizontalSep &&
        other.left < item.right + layoutConfig.horizontalSep;
      return isOverlap ? Math.max(max, stackOffset.get(other.id)! + other.height) : max;
    }, 0);
    stackOffset.set(item.id, offset);
  });

  // 行尾再算上本行展开内容的右边缘：内容可能比这一行的节点宽，伸到上方另一块内容底下
  const rowEnd = new Map<string, number>(
    ids.map((id) => {
      const { y } = points.get(id)!;
      const end = expansions.reduce((max, item) => {
        if (item.y !== y || item.x < rowStart.get(id)! || item.x > rowReach.get(id)!) {
          return max;
        }
        return Math.max(max, item.right);
      }, rowReach.get(id)!);
      return [id, end];
    }),
  );

  // 自上而下逐行算下移量，每一行取两类约束的最大值：
  // 1. 上方展开内容落在本行范围内，要让开它的底边。行尾停在展开点左边的行不在内容底下，不用让；
  //    同一行摞着的多块内容各按自己的底边算，压住自己的那块最靠下的决定下移量
  // 2. 上方与本行横向重叠的行，本行至少跟着它下移同样的距离。只看第 1 条的话，被更上方内容推下去的行
  //    会压到下方没被推的行上，比如嵌套并行里先收口的那条分支
  // 同一行的节点行首、行尾、纵坐标都一致，算出的下移量相同，整行不会被拆开
  const shiftMap = new Map<string, number>();
  [...ids]
    .sort((a, b) => points.get(a)!.y - points.get(b)!.y)
    .forEach((id) => {
      const { y } = points.get(id)!;
      const start = rowStart.get(id)!;
      const end = rowEnd.get(id)!;
      let shift = 0;
      expansions.forEach((item) => {
        if (item.y < y && item.x <= end) {
          shift = Math.max(shift, shiftMap.get(item.id)! + stackOffset.get(item.id)! + item.height);
        }
      });
      shiftMap.forEach((aboveShift, aboveId) => {
        if (points.get(aboveId)!.y < y && rowStart.get(aboveId)! <= end && start <= rowEnd.get(aboveId)!) {
          shift = Math.max(shift, aboveShift);
        }
      });
      shiftMap.set(id, shift);
    });

  // 骨架按折叠尺寸算，不知道展开内容比父节点宽出来的那一段。会被这一段压住的只有干线：它竖直跨过中间
  // 每一行下方的空档，而内容块正插在空档里。其余节点各占自己的行，内容块所在的行已被 shiftMap 腾空，
  // 碰不上，为它们让位纯属浪费横向空间。
  // 只看列在展开点右边的干线：pushAt 推的就是这些列，左边的干线原地不动，也够不到内容。
  // 同列取最宽的一块，跨列累加：右边的列要让开左边每一列多出来的宽度
  const columnOverhang = new Map<number, number>();
  expansions.forEach((item) => {
    const underTrunk = trunks.some((trunk) => trunk.column > item.x && trunk.top <= item.y && trunk.bottom > item.y);
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
    const point = points.get(id)!;
    const [width, height] = getNodeSize(model.nodeMap.get(id)!);
    const x = point.x + pushAt(point.x);
    const y = point.y + shiftMap.get(id)!;
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
 * 算好的位置。轮询每 10 秒来一次，变的只有状态，没有这层缓存每次都要把整套布局重算一遍。
 * 展开状态变了也只重算展开部分：每层的 dagre 骨架与展开无关，按层缓存，拓扑不变就不再重跑 dagre，
 * 大流程上 dagre 是肉眼可见的卡顿。
 * 生成器按画布实例创建，缓存不会在多个画布之间串
 */
export const createGraphDataBuilder = () => {
  const positionCache = new Map<string, Placement['positions']>();
  const skeletonCache = new Map<string, Skeleton>();
  let topologyKey = '';

  return async (model: FlowModel, { expandNodes, isSuperUserMode, searchKey }: GraphDataOptions) => {
    // 子流程的 pipeline 可能在轮询过程中才下发，节点会变多，这时布局必须重算
    const nextTopologyKey = [...model.nodeMap.keys()].join(',');
    if (nextTopologyKey !== topologyKey) {
      topologyKey = nextTopologyKey;
      positionCache.clear();
      skeletonCache.clear();
    }

    const expandKey = [...expandNodes].sort().join(',');
    let positions = positionCache.get(expandKey);
    if (!positions) {
      ({ positions } = await layoutPipeline('', model, expandNodes, skeletonCache));
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
