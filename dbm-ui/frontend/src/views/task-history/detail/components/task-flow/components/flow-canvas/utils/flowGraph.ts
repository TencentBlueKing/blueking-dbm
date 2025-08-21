import _ from 'lodash';

import { FlowTypes } from '@services/source/taskflow';

import { ExtensionCategory, Graph, type GraphData, GraphEvent, NodeEvent, register } from '@antv/g6';

import {
  type Edge,
  type FlowDetail,
  formatGraphData,
  generateCommonData,
  generateEdges,
  getewayTypes,
  type Node,
} from './calculate';
import CustomEdge from './customEdge';
import { GatewayNode } from './gatewayNode';
import { NormalNode, searchObj } from './normalNode';
import { StartEndNode } from './startEndNode';

const roundFlowTypes = [FlowTypes.EmptyEndEvent, FlowTypes.EmptyStartEvent, ...getewayTypes];

const targetNameHoverTypeMap: Record<string, string> = {
  forceFailWraper: 'forceFailHover',
  manualConfirmWraper: 'manualHover',
  retryWraper: 'retryHover',
  skipWraper: 'skipHover',
};

register(ExtensionCategory.NODE, FlowTypes.ConditionalParallelGateway, GatewayNode);
register(ExtensionCategory.NODE, FlowTypes.ConvergeGateway, GatewayNode);
register(ExtensionCategory.NODE, FlowTypes.ParallelGateway, GatewayNode);
register(ExtensionCategory.NODE, FlowTypes.ServiceActivity, NormalNode);
register(ExtensionCategory.NODE, FlowTypes.SubProcess, NormalNode);
register(ExtensionCategory.NODE, FlowTypes.EmptyStartEvent, StartEndNode);
register(ExtensionCategory.NODE, FlowTypes.EmptyEndEvent, StartEndNode);
register(ExtensionCategory.EDGE, 'custom-edge', CustomEdge);

export class FlowGraph {
  containerId = '';
  data: FlowDetail | null = null;
  edgesMap: Record<string, Set<string>> = {};
  expandNodeIds = new Set<string>();
  focusNodeId = '';
  graph: Graph | null = null;
  hoverNodeId = '';
  // isInit = false;
  nodesMap: Record<string, Node> = {};
  oldviewCenterPointer = [0, 0] as [number, number];
  searchObj = searchObj;
  totalEdges: Edge[] = [];
  viewZoom = 1;

  constructor(containerId: string) {
    this.containerId = containerId;
  }

  async collapseNode(id: string, isCollapse = true) {
    this.updateExpandNodeIds(id, isCollapse);
    this.renderNodes();
    await this.render();
  }

  destroy() {
    this.graph?.destroy();
  }

  fitView() {
    this.graph!.fitView();
  }

  async focusElement(nodeId: string) {
    await this.graph?.focusElement(nodeId);
    setTimeout(() => {
      const isVisible = this.isNodeVisible(nodeId);
      if (!isVisible) {
        this.focusElement(nodeId);
      }
    }, 500);
  }

  getClientByCanvas(client: [number, number]) {
    return this.graph!.getClientByCanvas(client);
  }

  getEdgeData() {
    return this.graph!.getEdgeData();
  }

  getElementPosition(nodeId: string) {
    return this.graph!.getElementPosition(nodeId);
  }

  getNodeData() {
    return this.graph!.getNodeData();
  }

  getOptions() {
    return this.graph!.getOptions();
  }

  getSize() {
    return this.graph!.getSize();
  }

  async initGraph(data?: FlowDetail) {
    if (!data) {
      return;
    }

    this.data = data;
    const commonData = generateCommonData(data);
    const edgesData = generateEdges(
      data,
      commonData.nodes,
      commonData.pipelineNodeToStartEventMap,
      commonData.outerStartEndEventIdMap,
    );
    this.edgesMap = edgesData.edgesMap;
    this.totalEdges = edgesData.edges;
    this.nodesMap = commonData.nodesMap;
    const { lines, locations } = formatGraphData(data, this.expandNodeIds);
    const graphData = {
      edges: lines,
      nodes: locations,
    };
    Array.from(document.getElementsByClassName('g6-minimap')).forEach((item) => {
      item.remove();
    });
    this.graph?.destroy();
    this.graph = new Graph({
      animation: false,
      behaviors: ['drag-canvas'],
      container: this.containerId,
      data: graphData as any,
      edge: {
        style: {
          endArrow: true,
          stroke: '#C4C6CC',
        },
        type: 'custom-edge',
      },
      node: {
        state: {
          // collapseBackgroundHover: {
          //   collapseBackgroundColor: '#979BA5',
          // },
          failedImageBackgroundColorHover: {
            failedImageBackgroundColor: '#FF0000',
          },
          finishedImageBackgroundColorHover: {
            finishedImageBackgroundColor: '#319B85',
          },
          focusNode: {
            focusNodeVisibility: 'visible',
          },
          forceFailHover: {
            forceFailOptFill: '#DCDEE5',
          },
          loadingImageBackgroundColorHover: {
            loadingImageBackgroundColor: '#1768EF',
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
            skipImageBackgroundColor: '#6CA633',
          },
          todoImageBackgroundColorHover: {
            todoImageBackgroundColor: '#E38B02',
          },
        },
        style: {
          // collapseBackgroundColor: '#C4C6CC',
          cursor: 'pointer',
          failedImageBackgroundColor: '#FF4D4D',
          fill: '#F5F7FA',
          finishedImageBackgroundColor: '#3DC2A6',
          focusNodeVisibility: 'hidden',
          forceFailOptFill: '#EAEBF0',
          loadingImageBackgroundColor: '#3A84FF',
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
          size: (d: any) => {
            if (roundFlowTypes.includes(d.type)) {
              return 48;
            } else if (d.pipeline) {
              return [254, 52];
            }
            return [240, 52];
          },
          skipImageBackgroundColor: '#7FBB44',
          skipOptFill: '#EAEBF0',
          todoImageBackgroundColor: '#F59500',
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

    this.graph.on(NodeEvent.POINTER_ENTER, (e: any) => {
      const { originalTarget, target } = e;
      const targetName = originalTarget.className;
      this.hoverNodeId = target.data.id;
      const state = this.graph!.getElementState(target.data.id) || [];
      if (targetName === 'backgroundShape') {
        // 背景加深
        this.graph!.setElementState(target.data.id, [...state, 'nodeBackgroundHover']);
        return;
      }
      // if (targetName === 'collapseBackground' || targetName === 'key') {
      //   // 折叠背景加深
      //   this.graph!.setElementState(target.data.id, [...state, 'collapseBackgroundHover']);
      //   return;
      // }
      if (targetName === 'rightTopBackground') {
        // 右上角背景加深
        let hoverState = '';
        switch (target.data.status) {
          case 'RUNNING':
            if (target.data.todoId) {
              hoverState = 'todoImageBackgroundColorHover';
            } else {
              hoverState = 'loadingImageBackgroundColorHover';
            }
            break;
          case 'FINISHED':
            if (target.data.skip) {
              hoverState = 'skipImageBackgroundColorHover';
            } else {
              hoverState = 'finishedImageBackgroundColorHover';
            }
            break;
          case 'FAILED':
            hoverState = 'failedImageBackgroundColorHover';
            break;
          case 'REVOKED':
            hoverState = 'failedImageBackgroundColorHover';
            break;
          default:
            break;
        }
        this.graph!.setElementState(target.data.id, [...state, hoverState]);
        return;
      }
      const hoverType = targetNameHoverTypeMap[targetName];
      // 操作按钮背景加深
      if (hoverType) {
        const state = this.graph!.getElementState(target.data.id) || [];
        this.graph!.setElementState(target.data.id, [...state, hoverType]);
      }
    });

    this.graph.on(NodeEvent.POINTER_LEAVE, () => {
      if (this.hoverNodeId) {
        this.graph?.setElementState(this.hoverNodeId, this.focusNodeId === this.hoverNodeId ? 'focusNode' : '');
        this.hoverNodeId = '';
      }
    });

    this.graph.on(
      GraphEvent.AFTER_TRANSFORM,
      _.debounce(() => {
        this.updateCanvasState();
      }, 100),
    );

    this.graph.on(GraphEvent.AFTER_RENDER, () => {
      // if (!this.isInit) {
      //   return;
      // }
      const newViewCenterPointer = this.graph!.getViewportCenter() as [number, number];
      this.graph!.translateBy([
        (newViewCenterPointer[0] - this.oldviewCenterPointer[0]) * this.viewZoom,
        (newViewCenterPointer[1] - this.oldviewCenterPointer[1]) * this.viewZoom,
      ]);
    });

    // this.updateNodeOrder(this.graphData.nodes);
    // await this.graph.render();
  }

  isNodeVisible(nodeId: string) {
    const position = this.graph!.getElementPosition(nodeId);
    const point = this.graph!.getViewportByCanvas(position);
    const [viewWidth, viewHeight] = this.graph!.getSize();
    return point[0] >= 0 && point[0] <= viewWidth && point[1] >= 0 && point[1] <= viewHeight;
  }

  on(eventName: string, callback: (...args: any[]) => void) {
    this.graph?.on(eventName, callback);
  }

  removeData(edges: Edge[], nodes: Node[]) {
    this.graph!.removeData({
      edges: edges.map((item) => item.id),
      nodes: nodes.map((item) => item.id),
    });
  }

  render() {
    return this.graph?.render();
  }

  renderNodes = () => {
    const { lines, locations } = formatGraphData(this.data!, this.expandNodeIds);
    const graphData = {
      edges: lines,
      nodes: locations,
    };
    this.graph?.setData(graphData as any);
  };

  setData(data: GraphData) {
    this.graph?.setData(data);
  }

  setElementState(nodeId: string, state: string | string[]) {
    this.graph?.setElementState(nodeId, state);
  }

  setOptions(options: Record<string, any>) {
    this.graph!.setOptions(options);
  }

  translateBy(offset: [number, number], animate?: any) {
    this.graph!.translateBy(offset, animate);
  }

  translateTo(point: [number, number], animate?: any) {
    this.graph!.translateTo(point, animate);
  }

  updateCanvasState() {
    this.viewZoom = this.graph!.getZoom();
    this.oldviewCenterPointer = this.graph!.getViewportCenter() as [number, number];
  }

  updateExpandNodeIds(id: string, isAdd = true) {
    if (isAdd) {
      this.expandNodeIds.add(id);
    } else {
      this.expandNodeIds.delete(id);
    }
  }

  updateFocusNode(nodeId: string, isForce = false) {
    if (this.focusNodeId === nodeId && !isForce) {
      return;
    }

    if (!isForce) {
      if (this.focusNodeId) {
        const node = this.getNodeData().find((item) => item.id === this.focusNodeId);
        if (node) {
          this.graph?.setElementState(this.focusNodeId, []);
        }
      }
    }
    this.focusNodeId = nodeId;
    this.graph?.setElementState(nodeId, 'focusNode');
  }

  updateNodeData(data: any) {
    this.graph?.updateNodeData(data);
  }

  zoomTo(zoom: number, animate?: any) {
    this.graph!.zoomTo(zoom, animate);
  }
}
