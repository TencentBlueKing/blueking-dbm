<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="flow-operation-main">
    <BkResizeLayout
      :border="false"
      class="resize-layout-main"
      collapsible
      :initial-divide="340"
      :is-collapsed="isCollapsed"
      :min="340"
      @after-resize="handleResizeLayout"
      @collapse-change="handleResizeLayout">
      <template #aside>
        <SearchTree
          ref="searchTreeRef"
          :data="treeData"
          :root-id="rootId"
          @node-click="handleNodeClick"
          @refresh="handleRefresh"
          @search="handleTreeSearch" />
      </template>
      <template #main>
        <FlowCanvas
          ref="flowCanvasRef"
          :data="data"
          :root-id="rootId"
          @click-single-node="handleShowLog"
          @refresh="handleRefresh" />
      </template>
    </BkResizeLayout>
  </div>
  <NodeDetail
    v-model:is-show="nodeOperationState.log.isShow"
    :node="nodeOperationState.currentNode"
    :root-id="rootId"
    :tree-data="treeData"
    @close="handleCloseNodeDetail"
    @refresh="handleRefresh" />
</template>
<script setup lang="tsx">
  import { type GraphData } from '@antv/g6';

  import FlowCanvas from './components/flow-canvas/Index.vue';
  import {
    type Edge,
    type FlowDetail,
    generateTreeData,
    getCurrentNodeChildenDataAndEdges,
    type Node,
    NormalNode,
    type TreeNode,
  } from './components/flow-canvas/utils';
  import NodeDetail from './components/node-detail/Index.vue';
  import SearchTree from './components/search-tree/Index.vue';

  interface Props {
    data?: FlowDetail;
  }

  type Emits = (e: 'refresh') => void;

  interface Exposes {
    checkAndInitCanvas: () => void;
    setTreeStatus: (status: string) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const route = useRoute();

  const treeData = ref<TreeNode[]>([]);
  const isCollapsed = ref(false);
  const searchTreeRef = ref<InstanceType<typeof SearchTree>>();
  const flowCanvasRef = ref<InstanceType<typeof FlowCanvas>>();

  const nodeOperationState = reactive({
    currentNode: undefined as Node | undefined,
    log: {
      isShow: false,
    },
  });

  const rootId = route.params.root_id as string;

  let totalEdges: Edge[] = [];
  let nodesMap: Record<string, Node> = {};

  watch(
    () => props.data,
    () => {
      // 只计算数量，当 待确认节点数 或 失败节点数 变化时，才刷新树结构
      if (props.data && props.data?.activities) {
        setTimeout(() => {
          const shareData = flowCanvasRef.value!.getShareData();
          nodesMap = shareData.nodesMap;
          const edgesMap = shareData.edgesMap;
          totalEdges = shareData.totalEdges;
          const rawTreeData = generateTreeData(props.data!, nodesMap, edgesMap) as TreeNode[];
          treeData.value = [
            props.data!.start_event as unknown as TreeNode,
            ...rawTreeData,
            props.data!.end_event as unknown as TreeNode,
          ];
          // 更新当前选中节点状态
          if (nodeOperationState.currentNode) {
            const currentNode = nodesMap[nodeOperationState.currentNode.id];
            if (currentNode) {
              nodeOperationState.currentNode = currentNode;
            }
          }
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleRefresh = () => {
    emits('refresh');
  };

  const handleResizeLayout = () => {
    setTimeout(() => {
      flowCanvasRef.value!.initGraph()!;
    }, 500);
  };

  const handleTreeSearch = (searchValue: string) => {
    const graph = flowCanvasRef.value!.getGraph()!;
    graph.searchObj.key = searchValue;
    flowCanvasRef.value!.initGraph()!;
  };

  const handleNodeClick = (node: TreeNode, parentNodes: TreeNode[]) => {
    // 展开并定位到目标节点
    // console.log('node = ', node);
    const graph = flowCanvasRef.value!.getGraph()!;
    const subProcessNodes = parentNodes.filter((item) => !!item.pipeline);
    if (subProcessNodes.length) {
      const { collapsedMap, graphData } = flowCanvasRef.value!.getShareData();
      const addAllEdges: Edge[] = [];
      const AddAllNodes: Node[] = [];
      subProcessNodes.forEach((subProcessNode) => {
        const realProcessNode = graph.getNodeData().find((item) => item.id === subProcessNode.id);
        if (realProcessNode) {
          realProcessNode.collapsed = true;
        }
        Object.assign(subProcessNode, {
          collapsed: true,
        });
        const { edges, nodes } = getCurrentNodeChildenDataAndEdges(subProcessNode.pipeline!, totalEdges);
        collapsedMap[subProcessNode.id] = {
          edges,
          nodes,
        };
        addAllEdges.push(...edges);
        AddAllNodes.push(...nodes);
      });
      const existedEdgeIds = new Set(graph.getEdgeData().map((item) => item.id));
      const existedNodeIds = new Set(graph.getNodeData().map((item) => item.id));
      const addEdges = addAllEdges.filter((item) => !existedEdgeIds.has(item.id));
      const addNodes = AddAllNodes.filter((item) => !existedNodeIds.has(item.id));
      if (addEdges.length || addNodes.length) {
        graphData.edges = [...addEdges, ...graph.getEdgeData()] as Edge[];
        graphData.nodes = [...addNodes, ...graph.getNodeData()] as Node[];
        graph.setData(graphData as unknown as GraphData);
        graph.render();
      }
    }
    setTimeout(async () => {
      await graph.focusElement(node.id);
      flowCanvasRef.value!.updateCanvasState();
    });
  };

  const handleShowLog = (node: NormalNode) => {
    if (node.data.status === 'CREATED') {
      return;
    }

    nodeOperationState.log.isShow = true;
    const targetNode = nodesMap[node.id];
    if (targetNode) {
      nodeOperationState.currentNode = targetNode;
    }
  };

  const handleCloseNodeDetail = () => {
    nodeOperationState.log.isShow = false;
  };

  defineExpose<Exposes>({
    checkAndInitCanvas: () => flowCanvasRef.value!.checkContainerInitCanvas(),
    setTreeStatus: (status: string) => searchTreeRef.value!.setStatus(status),
  });
</script>
<style lang="less">
  .flow-operation-main {
    display: flex;
    width: 100%;
    height: 100%;
    padding-right: 12px;

    .resize-layout-main {
      width: 100%;
      height: 100%;
    }
  }
</style>
