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
    <BkAlert
      v-if="isSuperUserMode"
      class="mb-16 ml-12"
      theme="warning"
      :title="t('已进入专家模式，当前可对所有失败节点执行强制操作。强制操作将绕过系统预设的流程控制，请谨慎操作。')" />
    <BkResizeLayout
      :border="false"
      class="resize-layout-main"
      :class="{ 'resize-layout-main-super-user': isSuperUserMode }"
      collapsible
      :initial-divide="330"
      :is-collapsed="isCollapsed"
      :max="500"
      :min="240"
      @after-resize="handleResizeLayout"
      @collapse-change="handleResizeLayout">
      <template #aside>
        <SearchTree
          ref="searchTreeRef"
          v-model:is-super-user-mode="isSuperUserMode"
          :data="treeData"
          :root-id="rootId"
          @node-click="handleNodeClick"
          @node-collapse="(node) => handleTreeCollapse(node, true)"
          @node-expand="(node) => handleTreeCollapse(node, false)"
          @refresh="handleRefresh"
          @search="handleTreeSearch"
          @view-log="(node) => handleShowLog(node)" />
      </template>
      <template #main>
        <FlowCanvas
          ref="flowCanvasRef"
          v-model:is-super-user-mode="isSuperUserMode"
          :data="data"
          :root-id="rootId"
          @click-single-node="handleShowLog"
          @ready="handleCanvasReady"
          @refresh="handleRefresh" />
      </template>
    </BkResizeLayout>
  </div>
  <NodeDetail
    v-model:is-show="nodeOperationState.log.isShow"
    :auto-open-ai-log="nodeOperationState.log.isShowAiLog"
    :flow-data="data"
    :node="nodeOperationState.currentNode"
    :root-id="rootId"
    :tree-data="treeData"
    @close="handleCloseNodeDetail"
    @refresh="handleRefresh" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import FlowCanvas from './components/flow-canvas/Index.vue';
  import { type FlowDetail, generateTreeData, type Node, type TreeNode } from './components/flow-canvas/utils';
  import NodeDetail from './components/node-detail/Index.vue';
  import SearchTree from './components/search-tree/Index.vue';

  interface Props {
    data?: FlowDetail;
  }

  interface Emits {
    (e: 'refresh'): void;
    (
      e: 'canvasReady',
      data: {
        nodesCount: number;
      },
    ): void;
  }

  interface Exposes {
    checkAndInitCanvas: () => void;
    setTreeStatus: (status: string) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();
  const isSuperUserMode = defineModel<boolean>('isSuperUserMode', { required: true });

  const route = useRoute();
  const { t } = useI18n();

  const treeData = ref<TreeNode[]>([]);
  const isCollapsed = ref(false);
  const searchTreeRef = ref<InstanceType<typeof SearchTree>>();
  const flowCanvasRef = ref<InstanceType<typeof FlowCanvas>>();

  const nodeOperationState = reactive({
    currentNode: undefined as Node | undefined,
    log: {
      isShow: false,
      isShowAiLog: false,
    },
  });

  const rootId = route.params.root_id as string;

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

  const handleCanvasReady = (data: { nodesCount: number }) => {
    emits('canvasReady', data);
  };

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

  const handleTreeCollapse = (node: TreeNode, isCollapsed: boolean) => {
    const flowGraphInstance = flowCanvasRef.value!.getGraph()!;
    const currentNode = flowGraphInstance.getNodeData().find((item) => item.id === node.id);
    if (!currentNode || currentNode.isExpand === !isCollapsed) {
      return;
    }

    flowGraphInstance.collapseNode(node.id);
    setTimeout(async () => {
      const isVisible = flowGraphInstance.isNodeVisible(node.id);
      if (!isVisible) {
        await flowGraphInstance.focusElement(node.id);
      }
      flowGraphInstance.updateFocusNode(node.id);
    });
  };

  const handleNodeClick = (node: TreeNode, parentNodes: TreeNode[]) => {
    const flowGraphInstance = flowCanvasRef.value!.getGraph()!;
    const subProcessNodes = parentNodes.filter((item) => !!item.pipeline);
    if (subProcessNodes.length) {
      const subProcessNodeIds = subProcessNodes.map((item) => item.id);
      subProcessNodeIds.forEach((id) => {
        flowGraphInstance.updateExpandNodeIds(id);
      });
      flowGraphInstance.renderNodes();
      flowGraphInstance.render();
    }
    setTimeout(async () => {
      const isVisible = flowGraphInstance.isNodeVisible(node.id);
      if (!isVisible) {
        await flowGraphInstance.focusElement(node.id);
      }

      flowGraphInstance.updateFocusNode(node.id);
      flowCanvasRef.value!.updateCanvasState();
    });
  };

  const handleShowLog = (node: any, isShowAiLog = false) => {
    if (node.data?.status === 'CREATED' || node.status === 'CREATED') {
      return;
    }
    nodeOperationState.log.isShow = true;
    nodeOperationState.log.isShowAiLog = isShowAiLog;
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
    // display: flex;
    width: 100%;
    height: 100%;
    padding-right: 12px;

    .resize-layout-main {
      width: 100%;
      height: 100%;
    }

    .resize-layout-main-super-user {
      height: calc(100% - 48px);
    }

    .bk-resize-layout-aside {
      border-right: none !important;
    }
  }
</style>
