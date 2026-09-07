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
    <div
      class="flow-content-main"
      :class="{ 'flow-content-main-super-user': isSuperUserMode }">
      <FlowCanvas
        ref="flowCanvasRef"
        v-model:expanded-ids="expandedIds"
        :left-offset="panelWidth"
        :model="model"
        :root-id="rootId"
        :search-key="searchKey"
        @click-single-node="handleShowLog"
        @ready="handleCanvasReady"
        @refresh="handleRefresh" />
      <div
        class="search-tree-panel"
        :class="{ 'is-resizing': isResizing }"
        :style="{ width: `${panelWidth}px` }">
        <div class="search-tree-panel-content">
          <SearchTree
            ref="searchTreeRef"
            :data="treeData"
            :expanded-ids="expandedIds"
            :root-id="rootId"
            :status-count="statusCount"
            @node-click="handleNodeClick"
            @node-collapse="(node) => handleTreeCollapse(node, true)"
            @node-expand="(node) => handleTreeCollapse(node, false)"
            @refresh="handleRefresh"
            @search="handleTreeSearch"
            @view-log="(node) => handleShowLog(node)" />
        </div>
        <div
          v-if="!isCollapsed"
          class="search-tree-panel-resize"
          @mousedown="handleResizeStart" />
        <div
          class="search-tree-panel-collapse"
          @click="handleToggleCollapse">
          <DbIcon :type="isCollapsed ? 'arrow-right' : 'arrow-left'" />
        </div>
      </div>
      <div
        v-if="isResizing"
        class="search-tree-panel-resize-mask" />
    </div>
  </div>
  <NodeDetail
    v-model:is-show="isNodeDetailShow"
    :auto-open-ai-log="isAutoOpenAiLog"
    :flow-data="data"
    :node="currentNode"
    :root-id="rootId"
    :tree-data="treeData"
    @close="handleCloseNodeDetail"
    @refresh="handleRefresh" />
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import {
    buildTree,
    type FlowDetail,
    type FlowModel,
    type FlowNode,
    type NodeStatusCount,
    superUserModeInjectionKey,
    type TreeNode,
  } from '@views/task-history/detail/utils';

  import FlowCanvas from './components/flow-canvas/Index.vue';
  import NodeDetail from './components/node-detail/Index.vue';
  import SearchTree from './components/search-tree/Index.vue';

  interface Props {
    data?: FlowDetail;
    model?: FlowModel;
    statusCount?: NodeStatusCount;
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
    model: undefined,
    statusCount: undefined,
  });
  const emits = defineEmits<Emits>();

  const PANEL_DEFAULT_WIDTH = 330;
  const PANEL_MIN_WIDTH = 240;
  const PANEL_MAX_WIDTH = 500;

  const route = useRoute();
  const { t } = useI18n();

  const isSuperUserMode = inject(superUserModeInjectionKey)!;

  const isCollapsed = ref(false);
  const isResizing = ref(false);
  const expandWidth = ref(PANEL_DEFAULT_WIDTH);
  const searchTreeRef = ref<InstanceType<typeof SearchTree>>();
  const flowCanvasRef = ref<InstanceType<typeof FlowCanvas>>();
  // 画布与搜索树共享的视图状态：展开的子流程、搜索关键字
  const expandedIds = ref<string[]>([]);
  const searchKey = ref('');
  const isNodeDetailShow = ref(false);
  const isAutoOpenAiLog = ref(false);
  const currentNodeId = ref('');

  // 折叠只把宽度归零，拖出来的宽度留着，再展开时按原宽度回来
  const panelWidth = computed(() => (isCollapsed.value ? 0 : expandWidth.value));
  const treeData = computed(() => (props.model ? buildTree(props.model) : []));
  // 从 model 里现取，轮询刷新后详情面板里的状态、耗时会跟着更新，不用再另设一次同步
  const currentNode = computed(() => props.model?.nodeMap.get(currentNodeId.value));

  const rootId = route.params.root_id as string;

  const resizeStart = {
    clientX: 0,
    width: 0,
  };

  const handleCanvasReady = (data: { nodesCount: number }) => {
    emits('canvasReady', data);
  };

  const handleRefresh = () => {
    emits('refresh');
  };

  // 面板浮在画布上层，拖动只改自身宽度，画布尺寸不受影响，不需要跟着同步
  const handleMouseMove = (moveEvent: MouseEvent) => {
    expandWidth.value = _.clamp(
      resizeStart.width + moveEvent.clientX - resizeStart.clientX,
      PANEL_MIN_WIDTH,
      PANEL_MAX_WIDTH,
    );
  };

  const handleMouseUp = () => {
    isResizing.value = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  const handleResizeStart = (event: MouseEvent) => {
    // 拖拽过程中不要选中树里的文字
    event.preventDefault();
    resizeStart.clientX = event.clientX;
    resizeStart.width = expandWidth.value;
    isResizing.value = true;

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleToggleCollapse = () => {
    isCollapsed.value = !isCollapsed.value;
  };

  const handleTreeSearch = (searchValue: string) => {
    searchKey.value = searchValue;
  };

  const setExpanded = (id: string, isExpanded: boolean) => {
    if (expandedIds.value.includes(id) === isExpanded) {
      return;
    }
    expandedIds.value = isExpanded ? [...expandedIds.value, id] : expandedIds.value.filter((item) => item !== id);
  };

  const handleTreeCollapse = (node: TreeNode, isCollapsed: boolean) => {
    setExpanded(node.id, !isCollapsed);
    // 收起时视口保持不动：用户只是想把这段内容折起来，不该被拉回子流程节点
    if (!isCollapsed) {
      flowCanvasRef.value!.focusNode(node.id);
    }
  };

  const handleNodeClick = (node: TreeNode, parentNodes: TreeNode[]) => {
    // 目标节点可能藏在若干层还没展开的子流程里，先把这些父级展开，画布上才有它
    const subProcessIds = parentNodes.filter((item) => !!item.pipeline).map((item) => item.id);
    const nextExpandedIds = _.union(expandedIds.value, subProcessIds);
    if (nextExpandedIds.length !== expandedIds.value.length) {
      expandedIds.value = nextExpandedIds;
    }
    flowCanvasRef.value!.focusNode(node.id);
  };

  const handleShowLog = (node: FlowNode, isShowAiLog = false) => {
    // 从画布点进来时树的高亮要跟着走；从树里点进来本来就是选中态，不会重复触发
    searchTreeRef.value!.setSelect(node.id);
    if (node.status === 'CREATED') {
      return;
    }
    currentNodeId.value = node.id;
    isAutoOpenAiLog.value = isShowAiLog;
    isNodeDetailShow.value = true;
  };

  const handleCloseNodeDetail = () => {
    isNodeDetailShow.value = false;
  };

  onBeforeUnmount(() => {
    // 拖到一半就切走的话，mouseup 收不到，监听要在这里兜底摘掉
    handleMouseUp();
  });

  defineExpose<Exposes>({
    checkAndInitCanvas: () => flowCanvasRef.value!.checkContainerInitCanvas(),
    setTreeStatus: (status: string) => searchTreeRef.value!.setStatus(status),
  });
</script>
<style lang="less">
  .flow-operation-main {
    width: 100%;
    height: 100%;
    padding-right: 12px;

    .flow-content-main {
      position: relative;
      width: 100%;
      height: 100%;
    }

    .flow-content-main-super-user {
      height: calc(100% - 48px);
    }

    .search-tree-panel {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 1;
      transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &.is-resizing {
        transition: none;
      }

      .search-tree-panel-content {
        height: 100%;
        overflow: hidden;
      }

      .search-tree-panel-resize {
        position: absolute;
        top: 0;
        bottom: 0;
        left: 100%;
        width: 8px;
        cursor: col-resize;
        border-left: 2px solid transparent;
        transition: all 0.15s;

        &:hover {
          border-color: #3a84ff;
        }
      }

      .search-tree-panel-collapse {
        position: absolute;
        top: 50%;
        left: 100%;
        z-index: 1;
        display: flex;
        width: 16px;
        height: 64px;
        color: #fff;
        cursor: pointer;
        background: #dcdee5;
        border-radius: 0 4px 4px 0;
        transform: translateY(-50%);
        align-items: center;
        justify-content: center;
        transition: all 0.15s;

        &:hover {
          background: #3a84ff;
        }
      }
    }

    .search-tree-panel-resize-mask {
      position: absolute;
      inset: 0;
      z-index: 2;
      cursor: col-resize;
    }
  }
</style>
