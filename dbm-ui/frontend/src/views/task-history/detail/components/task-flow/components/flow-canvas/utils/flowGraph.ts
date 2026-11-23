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

import { FlowTypes } from '@services/source/taskflow';

import {
  type FlowModel,
  getNodeDisplayStatus,
  NODE_STATUS_META,
  type NodeDisplayStatus,
} from '@views/task-history/detail/utils';

import {
  ExtensionCategory,
  Graph,
  GraphEvent,
  type IElementEvent,
  type IEvent,
  type NodeData,
  NodeEvent,
  register,
  type ViewportAnimationEffectTiming,
} from '@antv/g6';

import CustomEdge from './customEdge';
import { GatewayNode } from './gatewayNode';
import { createGraphDataBuilder, getNodeSize, type Node, roundFlowTypes } from './layout';
import { NormalNode } from './normalNode';
import { StartEndNode } from './startEndNode';

/** 画布渲染需要的全部输入，由组件从 props 组装后整体交给画布 */
export interface GraphInput {
  expandedIds: string[];
  isSuperUserMode: boolean;
  model: FlowModel;
  searchKey: string;
}

/**
 * 缩放配置，单位是百分比。
 * 快捷键与 Ctrl + 滚轮按 ZOOM_STEP 连续缩放，工具栏 ± 按钮与快捷下拉在 ZOOM_OPTIONS 的档位之间跳。
 * 范围取档位的首尾，否则下拉选出的档位会被 clamp 掉
 */
export const ZOOM_OPTIONS = [10, 25, 50, 75, 100, 150, 200, 300, 400];
export const ZOOM_MIN = ZOOM_OPTIONS[0];
export const ZOOM_MAX = ZOOM_OPTIONS[ZOOM_OPTIONS.length - 1];
export const ZOOM_STEP = 1;

// 定位后节点仍在可见区域外时的重试次数上限
const FOCUS_MAX_RETRY = 3;

// 节点离可见区域边缘多近算被挡住：失败节点卡片下方有操作按钮、跳过节点上方有标签，都不算在节点尺寸里
const FOCUS_VIEW_PADDING = 32;

// 确实要挪时在上面这段留白之外再往里走的距离，免得节点刚好卡在边缘上
const FOCUS_MOVE_INSET = 160;

// 平移动画时长
const FOCUS_MOVE_DURATION = 300;

const targetNameHoverTypeMap: Record<string, string> = {
  aiLogAnalysisWraper: 'aiLogHover',
  forceFailWraper: 'forceFailHover',
  manualConfirmWraper: 'manualHover',
  retryWraper: 'retryHover',
  skipWraper: 'skipHover',
};

// 右上角状态图标 hover 时加深。待执行的节点不画图标；执行中、准备中是自带底色的 gif，没有底色圆可加深
const statusHoverStateMap: Partial<Record<NodeDisplayStatus, string>> = {
  FAILED: 'failedImageBackgroundColorHover',
  FINISHED: 'finishedImageBackgroundColorHover',
  SKIPPED: 'skipImageBackgroundColorHover',
  TODO: 'todoImageBackgroundColorHover',
};

/**
 * 节点事件对应的布局后节点数据。
 * 三类自定义节点都有返回它的 data getter，但事件的 target 只标成 G6 的 Element，类型上看不到
 */
export const getEventNode = (e: IElementEvent) => (e.target as unknown as { data: Node }).data;

/**
 * 右上角状态图标由白底、彩色圆底、图标三层叠成（见 normalNode 的 drawStatusShape），
 * 指针落在哪一层都算在图标上。白底被彩色圆底盖住只剩一圈细边，只认白底的话几乎指不中
 */
export const isStatusIconShape = (className: string) => /^rightTop(Background|\w+Image(Background)?)$/.test(className);

register(ExtensionCategory.NODE, FlowTypes.ConditionalParallelGateway, GatewayNode);
register(ExtensionCategory.NODE, FlowTypes.ConvergeGateway, GatewayNode);
register(ExtensionCategory.NODE, FlowTypes.ParallelGateway, GatewayNode);
register(ExtensionCategory.NODE, FlowTypes.ServiceActivity, NormalNode);
register(ExtensionCategory.NODE, FlowTypes.SubProcess, NormalNode);
register(ExtensionCategory.NODE, FlowTypes.EmptyStartEvent, StartEndNode);
register(ExtensionCategory.NODE, FlowTypes.EmptyEndEvent, StartEndNode);
register(ExtensionCategory.EDGE, 'custom-edge', CustomEdge);

export class FlowGraph {
  container: HTMLElement;
  focusNodeId = '';
  focusRetryTimer: ReturnType<typeof setTimeout> | undefined = undefined;
  graph: Graph | null = null;
  hoverNodeId = '';
  /** 当前 hover 节点上已设置的 hover 态，指针在同一图形上移动时不重复设置 */
  hoverStateKey = '';
  input: GraphInput | null = null;
  /** 上一次记下的视口中心，用于补偿容器尺寸变化带来的位移。视口要等首次渲染才建起来，在那之前取不到 */
  oldviewCenterPointer: [number, number] | null = null;
  /** 见 applyGraphData */
  renderToken = 0;
  viewZoom = 1;

  private buildGraphData = createGraphDataBuilder();
  private moveFrameId = 0;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  /**
   * 算好布局再落地到画布。
   *
   * 布局是异步的，而轮询刷新、展开收起、树搜索都会走到这里，可能同时在途。
   * 后发起的那次算的是最新的展开状态，先发起的算完再落地就会把它覆盖回旧样子，
   * 所以发起时领一个序号，落地前确认自己仍是最新的一次。
   * 返回是否真的落地了
   */
  async applyGraphData() {
    this.renderToken += 1;
    const token = this.renderToken;
    const graphData = await this.getGraphData();
    if (token !== this.renderToken) {
      return false;
    }
    this.graph?.setData(graphData);
    return true;
  }

  /**
   * 输入变了，重新落一次数据。
   * 展开状态变化会改坐标，必须走 render 重新布局；只是节点状态或搜索词变了，draw 就够了
   */
  async applyInput(input: GraphInput, relayout = false) {
    this.input = input;
    if (await this.applyGraphData()) {
      await (relayout ? this.render() : this.draw());
    }
  }

  destroy() {
    clearTimeout(this.focusRetryTimer);
    cancelAnimationFrame(this.moveFrameId);
    this.graph?.destroy();
    this.graph = null;
  }

  /**
   * 只重绘元素，不重新布局。节点坐标由 createGraphDataBuilder 直接给出，
   * 轮询刷新时走这里比 render 少一次无意义的布局阶段
   */
  draw() {
    return this.graph?.draw();
  }

  /**
   * 聚焦节点。focusElement 结束后节点仍可能落在可见区域外（例如它在刚展开的子流程里，
   * 布局还没稳定），这里重试有限次，避免出现无终止的递归定时器
   */
  async focusElement(nodeId: string, leftOffset = 0, retryCount = FOCUS_MAX_RETRY) {
    clearTimeout(this.focusRetryTimer);
    // 节点可能已随子流程收起而不在画布上，G6 取不到元素会直接抛错
    if (!this.hasNode(nodeId)) {
      return;
    }
    await this.graph?.focusElement(nodeId);
    clearTimeout(this.focusRetryTimer);
    if (retryCount <= 0) {
      return;
    }
    this.focusRetryTimer = setTimeout(() => {
      if (this.graph && !this.isNodeVisible(nodeId, leftOffset)) {
        this.focusElement(nodeId, leftOffset, retryCount - 1);
      }
    }, 500);
  }

  getClientByCanvas(client: [number, number]) {
    return this.graph!.getClientByCanvas(client);
  }

  getElementPosition(nodeId: string) {
    return this.graph!.getElementPosition(nodeId) as [number, number];
  }

  getGraphData() {
    const { expandedIds, isSuperUserMode, model, searchKey } = this.input!;
    return this.buildGraphData(model, {
      expandNodes: new Set(expandedIds),
      isSuperUserMode,
      searchKey,
    });
  }

  getNodeData() {
    return this.graph!.getNodeData();
  }

  getSize() {
    return this.graph!.getSize();
  }

  /**
   * 浏览器坐标转视口坐标，缩放原点要的是后者。
   * Graph 没直接暴露这对转换，绕画布坐标一趟；原生 wheel 事件只给得到浏览器坐标
   */
  getViewportByClient(client: [number, number]) {
    return this.graph!.getViewportByCanvas(this.graph!.getCanvasByClient(client)) as [number, number];
  }

  /** 节点是否还在画布上。子流程收起后其中的节点会被移除，对它们设状态或定位 G6 都会抛错 */
  hasNode(nodeId: string) {
    return !!nodeId && !!this.graph?.hasNode(nodeId);
  }

  async initGraph(input: GraphInput) {
    this.input = input;

    // 图已经建过就不再重建。运行期拓扑是固定的，变的只有节点状态，
    // setData 会让 G6 自己做差异计算，视口、展开状态和运行中节点的旋转动画都能保住。
    // 判断与建图必须在同一个同步块里：隔着 await 判断的话，
    // 首屏布局还没算完时再进来一次，两次都会看到 graph 是 null 而各建一张图、各绑一套事件
    if (this.graph) {
      await this.applyInput(input);
      return;
    }

    // destroy 不会带走 minimap 的 DOM，重建前先清掉残留
    Array.from(document.getElementsByClassName('g6-minimap')).forEach((item) => {
      item.remove();
    });
    this.graph = new Graph({
      animation: false,
      behaviors: ['drag-canvas'],
      container: this.container,
      edge: {
        style: {
          endArrow: true,
          stroke: '#C4C6CC',
          // G6 默认把边排在节点之下（层级取两端节点的较大值再减一）。子流程节点包围盒左侧的
          // 14px 空档被基类整块的 key 图形盖住，箭头顶到展开收起图标上的那一截会被它裁掉，
          // 所以把边提到节点之上。代价是连线的每一段都必须落在卡片之外，见 customEdge 的 getEndpoints
          zIndex: 1,
        },
        type: 'custom-edge',
      },
      node: {
        state: {
          aiLogHover: {
            aiLogOptFill: '#DCDEE5',
          },
          failedImageBackgroundColorHover: {
            failedImageBackgroundColor: NODE_STATUS_META.FAILED.canvasHoverFill,
          },
          finishedImageBackgroundColorHover: {
            finishedImageBackgroundColor: NODE_STATUS_META.FINISHED.canvasHoverFill,
          },
          focusNode: {
            focusNodeVisibility: 'visible',
          },
          forceFailHover: {
            forceFailOptFill: '#DCDEE5',
          },
          manualHover: {
            manualOptFill: '#DCDEE5',
          },
          nodeBackgroundHover: {
            nodeBackgroundshadowColor: '#19192933',
          },
          retryHover: {
            retryOptFill: '#DCDEE5',
          },
          skipHover: {
            skipOptFill: '#DCDEE5',
          },
          skipImageBackgroundColorHover: {
            skipImageBackgroundColor: NODE_STATUS_META.SKIPPED.canvasHoverFill,
          },
          todoImageBackgroundColorHover: {
            todoImageBackgroundColor: NODE_STATUS_META.TODO.canvasHoverFill,
          },
        },
        style: {
          aiLogOptFill: '#EAEBF0',
          cursor: 'pointer',
          failedImageBackgroundColor: NODE_STATUS_META.FAILED.canvasFill,
          fill: '#F5F7FA',
          finishedImageBackgroundColor: NODE_STATUS_META.FINISHED.canvasFill,
          focusNodeVisibility: 'hidden',
          forceFailOptFill: '#EAEBF0',
          manualOptFill: '#EAEBF0',
          nodeBackgroundshadowColor: '#1919290d',
          ports: [{ placement: 'left' }, { placement: 'right' }],
          radius: (d: Node) => {
            if (roundFlowTypes.includes(d.type)) {
              return 29;
            }
            return 4;
          },
          retryOptFill: '#EAEBF0',
          // 形参类型由 G6 的 NodeStyle 定死，只能收到 NodeData 再转回来
          size: (d: NodeData) => getNodeSize(d as unknown as Node),
          skipImageBackgroundColor: NODE_STATUS_META.SKIPPED.canvasFill,
          skipOptFill: '#EAEBF0',
          todoImageBackgroundColor: NODE_STATUS_META.TODO.canvasFill,
        },
      },
      plugins: [
        {
          key: 'minimap',
          maskStyle: {
            background: '#3a84ff1a',
            border: '1px solid #3a84ff',
            borderRadius: 1,
          },
          position: 'top-right',
          size: [300, 160],
          type: 'minimap',
        },
      ],
      zoom: this.viewZoom,
    });

    // 用 pointerover 而不是 pointerenter：G6 的 node:pointerenter 由指针跨进另一个节点时合成，
    // 在节点内部从卡片挪到按钮上不会再触发；pointerover 逐个图形冒泡，指到哪个图形都能收到
    this.graph.on(NodeEvent.POINTER_OVER, (e: IElementEvent) => {
      const targetName = e.originalTarget.className;
      const node = getEventNode(e);
      // 指针在节点任何位置都加深背景，落在状态图标或操作按钮上时再加深对应图形
      let hoverState = '';
      if (isStatusIconShape(targetName)) {
        hoverState = statusHoverStateMap[getNodeDisplayStatus(node)] || '';
      } else {
        hoverState = targetNameHoverTypeMap[targetName] || '';
      }
      const stateKey = `${node.id}:${hoverState}`;
      if (stateKey === this.hoverStateKey) {
        return;
      }
      this.hoverNodeId = node.id;
      this.hoverStateKey = stateKey;
      // setElementState 是整体替换，聚焦态要一并带上
      const states = this.focusNodeId === node.id ? ['focusNode', 'nodeBackgroundHover'] : ['nodeBackgroundHover'];
      this.graph!.setElementState(node.id, hoverState ? [...states, hoverState] : states);
    });

    this.graph.on(NodeEvent.POINTER_LEAVE, () => {
      if (this.hoverNodeId && this.hasNode(this.hoverNodeId)) {
        this.graph!.setElementState(this.hoverNodeId, this.focusNodeId === this.hoverNodeId ? 'focusNode' : []);
      }
      this.hoverNodeId = '';
      this.hoverStateKey = '';
    });

    this.graph.on(
      GraphEvent.AFTER_TRANSFORM,
      _.debounce(() => {
        this.updateCanvasState();
      }, 100),
    );

    this.graph.on(GraphEvent.AFTER_RENDER, () => {
      const newViewCenterPointer = this.graph!.getViewportCenter() as [number, number];
      // 首次渲染之前没有视口中心可取，这一次没有基准可比，只把它记成基准，不补偿
      if (!this.oldviewCenterPointer) {
        this.oldviewCenterPointer = newViewCenterPointer;
        return;
      }
      this.graph!.translateBy([
        (newViewCenterPointer[0] - this.oldviewCenterPointer[0]) * this.viewZoom,
        (newViewCenterPointer[1] - this.oldviewCenterPointer[1]) * this.viewZoom,
      ]);
    });

    // 建图时不带 data，布局挪到这里算：这样上面的建图判断才能是同步的。
    // 首次的绘制交给调用方 render，它要先绑好自己的 AFTER_RENDER 监听
    await this.applyGraphData();
  }

  /**
   * 画布上的某个点是否还落在可见区域内，同样扣掉左侧浮动面板盖住的那一段。
   * 判的是点不是包围盒：挂在节点上的弹层只关心自己的锚点有没有被拖出去
   */
  isCanvasPointVisible(canvasPoint: [number, number], leftOffset = 0) {
    const [x, y] = this.graph!.getViewportByCanvas(canvasPoint) as [number, number];
    const [viewWidth, viewHeight] = this.getSize();
    return x >= leftOffset && x <= viewWidth && y >= 0 && y <= viewHeight;
  }

  /** 与 moveNodeIntoView 共用一套可见区域口径：按包围盒判断，并扣掉左侧浮动面板盖住的那一段 */
  isNodeVisible(nodeId: string, leftOffset = 0) {
    const [dx, dy] = this.getIntoViewOffset(nodeId, leftOffset);
    return !dx && !dy;
  }

  /**
   * 把节点挪进可见区域，只补被挡住的那个轴向。
   *
   * 不用 focusElement：它把节点移到视口正中，节点只在边界外露一点也会把整张画布挪一大段。
   * leftOffset 是左侧浮动面板的宽度，面板盖住的那一段画布不算可见区域。
   * 挪过之后坐标可能还会变（例如节点在刚展开的子流程里，布局还没稳定），复查有限次
   */
  moveNodeIntoView(nodeId: string, leftOffset = 0, retryCount = FOCUS_MAX_RETRY) {
    const [dx, dy] = this.getIntoViewOffset(nodeId, leftOffset);
    // 上一个聚焦节点的复查可能还在途，这次不管要不要挪都先清掉，否则它会把画布拽回旧节点
    clearTimeout(this.focusRetryTimer);
    if (!dx && !dy) {
      return;
    }
    this.animateTranslate(dx, dy);
    if (retryCount <= 0) {
      return;
    }
    this.focusRetryTimer = setTimeout(() => {
      if (this.graph) {
        this.moveNodeIntoView(nodeId, leftOffset, retryCount - 1);
      }
    }, 500);
  }

  on<T extends IEvent>(eventName: string, callback: (event: T) => void) {
    this.graph?.on(eventName, callback);
  }

  render() {
    return this.graph?.render();
  }

  /**
   * 容器尺寸变化时同步画布尺寸。布局坐标只由节点宽高与间距决定，与容器大小无关，
   * 所以不需要重建整张图
   */
  resize() {
    this.graph?.resize();
  }

  translateBy(offset: [number, number], animate?: ViewportAnimationEffectTiming) {
    this.graph!.translateBy(offset, animate);
  }

  translateTo(point: [number, number], animate?: ViewportAnimationEffectTiming) {
    this.graph!.translateTo(point, animate);
  }

  updateCanvasState() {
    this.viewZoom = this.graph!.getZoom();
    this.oldviewCenterPointer = this.graph!.getViewportCenter() as [number, number];
  }

  updateFocusNode(nodeId: string, isForce = false) {
    if (this.focusNodeId === nodeId && !isForce) {
      return;
    }

    if (!isForce && this.hasNode(this.focusNodeId)) {
      this.graph?.setElementState(this.focusNodeId, []);
    }
    // 聚焦节点可能已随子流程收起被移除，不再记着它：否则复位会去定位一个不存在的节点
    if (!this.hasNode(nodeId)) {
      this.focusNodeId = '';
      return;
    }
    this.focusNodeId = nodeId;
    // setElementState 整体替换状态，hover 态随之被抹掉，记录一并清掉，指针再动一下就能重新加深
    this.hoverStateKey = '';
    this.graph?.setElementState(nodeId, 'focusNode');
  }

  // origin 是缩放锚点的视口坐标，不传则按视口中心缩放。
  // 建图时 animation 是 false，G6 会忽略逐次传入的动画配置，这里不再接收动画参数
  zoomTo(zoom: number, origin?: [number, number]) {
    // AFTER_TRANSFORM 是防抖的，这里同步记一份，避免这段时间里的视口补偿按旧倍率算
    this.viewZoom = zoom;
    this.graph!.zoomTo(zoom, false, origin);
    // 按视口中心缩放时中心点不动，锚在指针上则会挪动，同理不能等防抖：
    // 否则这段时间里落地的 render 会拿旧中心算出一段偏移，补偿成一次跳动。
    // G6 对「有 origin 且无动画」走同步快路径，这里读到的已经是缩放后的值
    if (origin) {
      this.oldviewCenterPointer = this.graph!.getViewportCenter() as [number, number];
    }
  }

  /**
   * 分帧平移，而不是把动画配置交给 translateBy：建图时 animation 是 false，
   * G6 会把逐次传入的动画配置一并忽略，而打开全局开关会连带影响元素动画与滚轮缩放的手感。
   * 每帧只补当帧的增量，中途用户拖动或滚动画布时两段位移叠加，不会把画布拽回去
   */
  private animateTranslate(dx: number, dy: number) {
    cancelAnimationFrame(this.moveFrameId);
    const startTime = performance.now();
    let applied = 0;

    const step = () => {
      if (!this.graph) {
        return;
      }
      const progress = Math.min((performance.now() - startTime) / FOCUS_MOVE_DURATION, 1);
      // ease-out，起步快收尾慢
      const eased = 1 - (1 - progress) ** 3;
      this.graph.translateBy([(eased - applied) * dx, (eased - applied) * dy]);
      applied = eased;
      if (progress < 1) {
        this.moveFrameId = requestAnimationFrame(step);
      }
    };

    this.moveFrameId = requestAnimationFrame(step);
  }

  /**
   * 节点进入可见区域所需的位移，单位是视口像素。
   * 逐轴判断：只有这个轴向被挡住才给位移，两个轴向都在可见区域内就是 [0, 0]
   */
  private getIntoViewOffset(nodeId: string, leftOffset: number): [number, number] {
    const node = this.getNodeData().find((item) => item.id === nodeId);
    if (!node) {
      return [0, 0];
    }

    const [centerX, centerY] = this.getElementPosition(nodeId);
    const [width, height] = getNodeSize(node as unknown as Node);
    // 取包围盒的两个角转视口坐标，缩放倍率一并折进去
    const [left, top] = this.graph!.getViewportByCanvas([centerX - width / 2, centerY - height / 2]);
    const [right, bottom] = this.graph!.getViewportByCanvas([centerX + width / 2, centerY + height / 2]);
    const [viewWidth, viewHeight] = this.getSize();

    // 被挡住的那一侧不是挪到刚好进来，而是多往里走一段
    const axisOffset = (start: number, end: number, min: number, max: number) => {
      if (start >= min && end <= max) {
        return 0;
      }
      // 富余空间不够两倍余量时对半分，节点比可见区域还大（面板拉宽又缩小窗口）则退化为居中
      const inset = Math.min(FOCUS_MOVE_INSET, (max - min - (end - start)) / 2);
      return start < min ? min + inset - start : max - inset - end;
    };

    return [
      axisOffset(left, right, leftOffset + FOCUS_VIEW_PADDING, viewWidth - FOCUS_VIEW_PADDING),
      axisOffset(top, bottom, FOCUS_VIEW_PADDING, viewHeight - FOCUS_VIEW_PADDING),
    ];
  }
}
