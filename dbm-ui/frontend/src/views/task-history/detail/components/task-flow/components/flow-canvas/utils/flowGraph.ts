import _ from 'lodash';

import { FlowTypes } from '@services/source/taskflow';

import { ExtensionCategory, Graph, type GraphData, GraphEvent, NodeEvent, register } from '@antv/g6';

import {
  type Edge,
  type FlowDetail,
  generateCommonData,
  generateEdges,
  getCurrentNodeChildenDataAndEdges,
  getewayTypes,
  type Node,
} from './calculate';
import CustomEdge from './customEdge';
import { GatewayNode } from './gatewayNode';
import { NormalNode, searchObj } from './normalNode';
import { StartEndNode } from './startEndNode';

const roundFlowTypes = [FlowTypes.EmptyEndEvent, FlowTypes.EmptyStartEvent, ...getewayTypes];

const targetNameHoverTypeMap: Record<string, string> = {
  forceFailWraper: 'hoverForceFail',
  manualConfirmWraper: 'hoverManual',
  retryWraper: 'hoverRetry',
  skipWraper: 'hoverSkip',
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
  // 展开记录
  collapsedMap: Record<
    string,
    {
      edges: Edge[];
      nodes: Node[];
    }
  > = {};
  containerId = '';
  edgesMap: Record<string, Set<string>> = {};
  focusNodeId = '';
  graph: Graph | null = null;
  graphData: {
    edges: Edge[];
    nodes: Node[];
  } = {
    edges: [],
    nodes: [],
  };
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

  collapseNode(node: Node, isCollapse: boolean) {
    if (!isCollapse) {
      if (this.collapsedMap[node.id]) {
        const { nodes } = this.removeCollapsedData(node.id);
        this.updateNodeOrder(nodes, false);
      } else {
        const { edges, nodes } = getCurrentNodeChildenDataAndEdges(node.pipeline!, this.totalEdges);
        this.removeData(edges, nodes);
        this.updateNodeOrder(nodes, false);
      }
    } else {
      if (this.collapsedMap[node.id]) {
        this.graph!.addData(this.collapsedMap[node.id] as unknown as GraphData);
        this.updateNodeOrder(this.collapsedMap[node.id].nodes);
      } else {
        const { edges, nodes } = getCurrentNodeChildenDataAndEdges(node.pipeline!, this.totalEdges);
        this.collapsedMap[node.id] = {
          edges,
          nodes,
        };
        this.updateNodeOrder(nodes);
        this.graphData.edges = [...this.graphData.edges, ...edges];
        this.graphData.nodes = [...this.graphData.nodes, ...nodes];
        this.graph!.addData({
          edges: edges as unknown as GraphData['edges'],
          nodes: nodes as any,
        });
      }
    }
  }

  destroy() {
    this.graph?.destroy();
  }

  fitView() {
    this.graph!.fitView();
  }

  focusElement(nodeId: string) {
    return this.graph?.focusElement(nodeId);
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
    if (!this.graphData.nodes.length) {
      const { edges, nodes } = getCurrentNodeChildenDataAndEdges(data, this.totalEdges, true);
      this.graphData.edges = edges;
      this.graphData.nodes = nodes;
    } else {
      this.graphData.nodes.forEach((node) => {
        if (this.nodesMap[node.id]) {
          Object.assign(node, this.nodesMap[node.id]);
        }
      });
    }

    Array.from(document.getElementsByClassName('g6-minimap')).forEach((item) => {
      item.remove();
    });
    this.graph?.destroy();
    // console.log('this.graphData = ', this.graphData);
    this.graph = new Graph({
      animation: false,
      behaviors: ['drag-canvas'],
      container: this.containerId,
      data: this.graphData as any,
      edge: {
        style: {
          // startArrow: true, // 起始端箭头
          // startArrowType: 'circle',
          endArrow: true,
          stroke: '#C4C6CC',
        },
        type: 'cubic-horizontal',
        // type: 'custom-edge',
      },
      layout: {
        align: 'UL',
        // type: 'dagre',
        nodeOrder: [],
        // 垂直间距
        nodesep: 16,
        rankdir: 'LR',
        // 水平间距
        ranksep: 20,
        type: 'antv-dagre',
      },
      node: {
        state: {
          focus: {
            focusState: 'visible',
          },
          hoverForceFail: {
            forceFailOptFill: '#DCDEE5',
          },
          hoverManual: {
            manualOptFill: '#DCDEE5',
          },
          hoverRetry: {
            retryOptFill: '#DCDEE5',
          },
          hoverSkip: {
            skipOptFill: '#DCDEE5',
          },
        },
        style: {
          cursor: 'pointer',
          fill: '#F5F7FA',
          focusState: 'hidden',
          forceFailOptFill: '#EAEBF0',
          manualOptFill: '#EAEBF0',
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
          skipOptFill: '#EAEBF0',
        },
      },
      // padding: 0,
      plugins: [
        {
          key: 'minimap',
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
      const hoverType = targetNameHoverTypeMap[targetName];
      if (hoverType) {
        this.hoverNodeId = target.data.id;
        const state = this.graph!.getElementState(target.data.id) || [];
        this.graph!.setElementState(target.data.id, [...state, hoverType]);
      }
    });

    this.graph.on(NodeEvent.POINTER_LEAVE, () => {
      if (this.hoverNodeId) {
        this.graph?.setElementState(this.hoverNodeId, this.focusNodeId === this.hoverNodeId ? 'focus' : '');
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

    this.updateNodeOrder(this.graphData.nodes);
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

  removeCollapsedData(removeNodeId: string) {
    const { edges, nodes } = this.collapsedMap[removeNodeId];
    delete this.collapsedMap[removeNodeId];
    const removeEdges = _.cloneDeep(edges);
    const removeNodes = _.cloneDeep(nodes);
    const findRelatedNodeData = (nodeList: Node[]) => {
      nodeList.forEach((node) => {
        if (this.collapsedMap[node.id]) {
          const { edges, nodes } = this.collapsedMap[node.id];
          delete this.collapsedMap[node.id];
          removeEdges.push(...edges);
          removeNodes.push(...nodes);
          findRelatedNodeData(nodes);
        }
      });
    };
    findRelatedNodeData(removeNodes);
    this.removeData(removeEdges, removeNodes);
    return {
      edges: removeEdges,
      nodes: removeNodes,
    };
  }

  removeData(edges: Edge[], nodes: Node[]) {
    this.graph!.removeData({
      edges: edges.map((item) => item.id),
      nodes: nodes.map((item) => item.id),
    });
    this.removeDataFromGraphData(edges, nodes);
  }

  removeDataFromGraphData(edges: Edge[], nodes: Node[]) {
    const removeEdgeIdMap = edges.reduce<Record<string, boolean>>(
      (idMap, item) =>
        Object.assign(idMap, {
          [item.id]: true,
        }),
      {},
    );
    const removeNodeIdMap = nodes.reduce<Record<string, boolean>>(
      (idMap, item) =>
        Object.assign(idMap, {
          [item.id]: true,
        }),
      {},
    );
    this.graphData.edges = this.graphData.edges.filter((item) => !removeEdgeIdMap[item.id]);
    this.graphData.nodes = this.graphData.nodes.filter((item) => !removeNodeIdMap[item.id]);
  }

  render() {
    return this.graph?.render();
  }

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

  updateCanvasState() {
    this.viewZoom = this.graph!.getZoom();
    this.oldviewCenterPointer = this.graph!.getViewportCenter() as [number, number];
  }

  updateFocusNode(nodeId: string, isForce = false) {
    if (this.focusNodeId === nodeId && !isForce) {
      return;
    }

    if (!isForce) {
      if (this.focusNodeId) {
        const node = this.graphData.nodes.find((item) => item.id === this.focusNodeId);
        if (node) {
          this.graph?.setElementState(this.focusNodeId, []);
        }
      }
    }
    this.focusNodeId = nodeId;
    this.graph?.setElementState(nodeId, 'focus');
  }

  updateNodeData(data: any) {
    this.graph?.updateNodeData(data);
  }

  updateNodeOrder(nodes: Node[], isAdd = true) {
    const options = this.getOptions() as any;
    console.log('options = ', options);
    const targetNodes = nodes.filter(
      (node) => this.edgesMap[node.id]?.size > 1 && node.children && node.children.length > 1,
    );
    const targetOrderNodeIds = _.flatMap(targetNodes.map((node) => node.children!.map((item) => item.id)));
    if (!targetOrderNodeIds.length) {
      return;
    }

    if (isAdd && options.layout.nodeOrder.includes(targetOrderNodeIds[0])) {
      return;
    }

    if (!isAdd) {
      // 移除 orderNodes
      const orderNodes = _.difference(options.layout.nodeOrder, targetOrderNodeIds);
      options.layout.nodeOrder = orderNodes;
    } else {
      // 新增 orderNodes
      options.layout.nodeOrder.push(...targetOrderNodeIds);
    }
    this.setOptions(options);
  }
  zoomTo(zoom: number, animate: any) {
    this.graph!.zoomTo(zoom, animate);
  }
}
