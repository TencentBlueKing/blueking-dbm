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
  <div class="search-tree-main">
    <div class="status-select-main">
      <div class="select-title">{{ t('节点状态') }}</div>
      <BkSelect
        v-model="statusValue"
        class="select-box"
        :clearable="false"
        :filterable="false"
        :input-search="false"
        @change="handleSelectChange"
        @toggle="handleSelectToggle">
        <BkOption
          v-for="(item, index) in statusList"
          :key="index"
          :label="item.label"
          :value="item.value">
          <StatusSign
            :class="item.value === 'ALL' ? 'mr-4' : 'mr-8'"
            :data="item.value" />
          <span>{{ item.label }}</span>
        </BkOption>
        <template #trigger>
          <div
            class="select-result-display"
            :style="{ borderColor: isSelectPanelOpen ? '#3a84ff !important' : '#f0f1f5' }">
            <StatusSign
              class="mr-8"
              :data="statusValue" />
            <div
              v-overflow-tips
              class="display-txt">
              {{ statusDisplay }}
            </div>
            <DbIcon
              class="arrow-icon"
              type="down-big" />
          </div>
        </template>
      </BkSelect>
    </div>
    <BkInput
      v-model="treeSearch"
      class="search-input"
      clearable
      :placeholder="t('请输入节点名称')"
      type="search" />
    <BkTree
      ref="treeRef"
      class="flow-tree-main"
      :data="renderTreeData"
      label="name"
      node-key="id"
      :search="treeSearch"
      :show-checkbox="showBatchOperation"
      :show-node-type-icon="false"
      @node-checked="handleNodeChecked"
      @node-click="handleNodeClick"
      @node-collapse="handleNodeCollapse"
      @node-expand="handleNodeExpand">
      <template #node="item">
        <div
          class="task-detail-tree-node"
          :class="{ 'is-sub-process': !!item.children }">
          <FlowSign
            :status="getNodeDisplayStatus(item)"
            :type="item.type" />
          <span
            v-overflow-tips="{ content: item.name, placement: 'right' }"
            class="text-overflow node-name">
            {{ item.name }}
          </span>
          <div
            v-if="item.type === FlowTypes.ServiceActivity"
            class="view-log-main">
            <BkButton
              text
              theme="primary"
              @click.stop="handleViewLog(item)">
              <DbIcon type="form" />
              <span style="margin-left: 5px; font-size: 12px">{{ t('节点详情') }}</span>
            </BkButton>
          </div>
        </div>
      </template>
    </BkTree>
    <BatchOperation
      v-if="showBatchOperation"
      ref="batchOperationRef"
      :data="selectedNodes"
      :root-id="rootId"
      :status="statusValue"
      @cancel="handleCancelCheck"
      @check-all="handleCheckAll"
      @refresh="handleRefresh" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { FlowTypes } from '@services/source/taskflow';

  import {
    generateDifferentStatusTreeData,
    getNodeDisplayStatus,
    NODE_STATUS_META,
    type NodeStatusCount,
    type TreeNode,
  } from '@views/task-history/detail/utils';

  import BatchOperation from './components/BatchOperation.vue';
  import FlowSign from './components/FlowSign.vue';
  import StatusSign from './components/StatusSign.vue';

  interface Props {
    data: TreeNode[];
    /** 画布上已展开的子流程 id，树要跟着展开到同一份状态 */
    expandedIds: string[];
    rootId: string;
    statusCount?: NodeStatusCount;
  }

  interface Emits {
    (e: 'search', value: string): void;
    (e: 'node-click', node: TreeNode, parentNodes: TreeNode[]): void;
    (e: 'refresh'): void;
    (e: 'node-collapse', node: TreeNode): void;
    (e: 'node-expand', node: TreeNode): void;
    (e: 'view-log', node: TreeNode): void;
  }

  interface Exposes {
    setSelect(id: string): void;
    setStatus(value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  // 筛选下拉的选项按执行先后排。准备中与执行中同色，画布图例里没有单列这一项
  const FILTER_STATUS_LIST = ['CREATED', 'READY', 'RUNNING', 'FINISHED', 'FAILED', 'TODO'] as const;

  const { t } = useI18n();

  const treeRef = ref();
  const treeSearch = ref('');
  const statusValue = ref('ALL');
  const isSelectPanelOpen = ref(false);
  const selectFlows = ref<TreeNode[]>([]);
  const selectedNodes = ref<TreeNode[]>([]);
  const batchOperationRef = ref<InstanceType<typeof BatchOperation>>();

  const renderTreeData = computed(() => {
    if (statusValue.value === 'ALL') {
      return props.data;
    }

    return generateDifferentStatusTreeData(props.data, statusValue.value);
  });

  // 计数由上层统一从 model 算好传进来，和顶部状态角标同一口径
  const statusList = computed(() => [
    {
      label: `${t('全部')} ( ${props.statusCount?.ALL ?? 0} )`,
      value: 'ALL',
    },
    ...FILTER_STATUS_LIST.map((status) => ({
      label: `${NODE_STATUS_META[status].text} ( ${props.statusCount?.[status] ?? 0} )`,
      value: status as string,
    })),
  ]);

  const statusDisplay = computed(() => statusList.value.find((item) => item.value === statusValue.value)!.label);
  const showBatchOperation = computed(
    () => ['FAILED', 'RUNNING', 'TODO'].includes(statusValue.value) && renderTreeData.value.length > 0,
  );

  const openedTreeNodesSet = new Set<string>();
  const checkedTreeNodesSet = new Set<string>();
  let currentClickNode = '';
  let isCheckedClick = false;

  watch(treeSearch, () => {
    emitSearch(treeSearch.value);
    if (!treeSearch.value) {
      return;
    }

    batchSetTreeNodeOpen();
  });

  watch(statusValue, async () => {
    if (statusValue.value === 'ALL') {
      return;
    }
    // 等 renderTreeData 重新渲染完，树里才有筛选后的节点
    await nextTick();
    batchSetTreeNodeOpen();
    const firstLeafNode = findFirstLeafNode(renderTreeData.value);
    if (!firstLeafNode) {
      return;
    }

    // 只把树的高亮挪过去，不联动画布：用户可能只是想看看失败节点有哪些，画布不该跟着跳走
    selectTreeNode(firstLeafNode);
  });

  // 画布上展开、收起子流程后同步过来。树自己的展开走 handleNodeExpand / handleNodeCollapse，
  // 两边共用 openedTreeNodesSet，轮询刷新时才能一起贴回去
  watch(
    () => props.expandedIds,
    () => {
      if (!treeRef.value) {
        return;
      }

      const expandedIdSet = new Set(props.expandedIds);
      flattenTreeData(renderTreeData.value).forEach((node) => {
        // 扇出网关的分支只在树里展得开，不由 expandedIds 驱动
        if (!node.pipeline) {
          return;
        }
        const isExpanded = expandedIdSet.has(node.id);
        if (isExpanded === openedTreeNodesSet.has(node.id)) {
          return;
        }
        // setOpen 不会再抛 node-expand / node-collapse，不必担心绕回画布
        treeRef.value!.setOpen(node, isExpanded);
        if (isExpanded) {
          openedTreeNodesSet.add(node.id);
        } else {
          forgetOpened(node);
        }
      });
    },
  );

  // 轮询刷新后树数据整份替换，展开、勾选、选中状态要按 id 重新贴回去
  watch(
    () => props.data,
    async () => {
      await nextTick();
      if (!treeRef.value) {
        return;
      }

      if (treeSearch.value) {
        batchSetTreeNodeOpen();
        return;
      }

      const newTreeDataList = treeRef.value.getData().data as TreeNode[];
      newTreeDataList.forEach((item) => {
        if (openedTreeNodesSet.has(item.id)) {
          treeRef.value!.setOpen(item);
        }
        if (checkedTreeNodesSet.has(item.id)) {
          treeRef.value!.setChecked(item, true);
        }
        if (item.id === currentClickNode) {
          treeRef.value!.setSelect(item);
        }
      });
    },
    {
      immediate: true,
    },
  );

  const batchSetTreeNodeOpen = _.debounce(() => {
    const list = flattenTreeData(renderTreeData.value);
    list.forEach((item) => {
      if (item.children?.length) {
        treeRef.value!.setOpen(item);
        openedTreeNodesSet.add(item.id);
      }
    });
  }, 500);

  // 树按 treeSearch 即时过滤，画布的高亮要跟着走。防抖是为了不让每个按键都触发一次画布重绘
  const emitSearch = _.debounce((value: string) => {
    emits('search', value);
  }, 300);

  const findFirstLeafNode = (data: TreeNode[]) => {
    const list = flattenTreeData(data);
    return list.find((item) => item.type === FlowTypes.ServiceActivity);
  };

  const handleSelectChange = () => {
    selectedNodes.value = [];
  };

  const handleViewLog = (node: TreeNode) => {
    emits('view-log', node);
  };

  const handleRefresh = () => {
    emits('refresh');
    selectedNodes.value = [];
    checkedTreeNodesSet.clear();
  };

  const flattenTreeData = (data: TreeNode[]) => {
    const list: TreeNode[] = [];

    const deepFlatTreeData = (data: TreeNode[]) => {
      data.forEach((item) => {
        list.push(item);
        if (item.children) {
          deepFlatTreeData(item.children);
        }
      });
    };
    deepFlatTreeData(data);
    return list;
  };

  const handleNodeExpand = (node: TreeNode) => {
    openedTreeNodesSet.add(node.id);
    if (node.pipeline) {
      emits('node-expand', node);
    }
  };

  // 收起时子孙也跟着收起。子孙就在 node.children 上，沿着它走一遍即可，
  // 不必再另建一张 id 到子孙 id 的映射
  const forgetOpened = (node: TreeNode) => {
    openedTreeNodesSet.delete(node.id);
    node.children?.forEach(forgetOpened);
  };

  const handleNodeCollapse = (node: TreeNode) => {
    forgetOpened(node);
    if (node.pipeline) {
      emits('node-collapse', node);
    }
  };

  const getParentNodes = (node: TreeNode) => {
    const parentNodes: TreeNode[] = [];
    let parentNode = treeRef.value!.getParentNode(node);
    while (parentNode) {
      parentNodes.unshift(parentNode);
      parentNode = treeRef.value!.getParentNode(parentNode);
    }
    return parentNodes;
  };

  // 只挪树的高亮，要不要联动画布由各个调用点自己决定
  const selectTreeNode = (node: TreeNode) => {
    currentClickNode = node.id;
    // setSelect 会连带展开目标节点的父级，展开态一并记下来，轮询刷新后才贴得回去
    getParentNodes(node).forEach((item) => {
      openedTreeNodesSet.add(item.id);
    });
    treeRef.value!.setSelect(node);
  };

  const handleSelectToggle = (isOpen: boolean) => {
    isSelectPanelOpen.value = isOpen;
  };

  const handleNodeClick = (node: TreeNode) => {
    if (isCheckedClick) {
      return;
    }
    currentClickNode = node.id;
    emits('node-click', node, getParentNodes(node));
  };

  const handleNodeChecked = (list: TreeNode[]) => {
    // 点复选框时 BkTree 会连带抛一次 node-click，这里标记一下让紧随其后的那次点击不生效。
    // 两个事件是同一个任务里同步抛出来的，用微任务复位，万一没有后续的 node-click，
    // 标记也不会残留到下一次真实点击
    isCheckedClick = true;
    Promise.resolve().then(() => {
      isCheckedClick = false;
    });
    checkedTreeNodesSet.clear();
    // 只需要选中最终的叶子节点即可
    list.forEach((item) => {
      if (item.children && item.children.length) {
        return;
      }

      checkedTreeNodesSet.add(item.id);
    });
    selectFlows.value = list;
    const nodeList = list.filter((item) => item.type === FlowTypes.ServiceActivity);
    selectedNodes.value = nodeList;
    const allNodes = flattenTreeData(renderTreeData.value);
    if (list.length === allNodes.length) {
      batchOperationRef.value!.setCheckAll(true);
    } else {
      batchOperationRef.value!.setCheckAll(false);
    }
  };

  const handleCancelCheck = () => {
    treeRef.value!.setChecked(selectFlows.value, false);
    selectedNodes.value = [];
    checkedTreeNodesSet.clear();
  };

  const handleCheckAll = (isCheckAll: boolean) => {
    const allNodes = flattenTreeData(renderTreeData.value);
    treeRef.value!.setChecked(allNodes, isCheckAll);
    if (isCheckAll) {
      handleNodeChecked(allNodes);
    } else {
      handleCancelCheck();
    }
  };

  onBeforeUnmount(() => {
    batchSetTreeNodeOpen.cancel();
    emitSearch.cancel();
  });

  defineExpose<Exposes>({
    setSelect(id: string) {
      if (currentClickNode === id) {
        return;
      }
      const node = flattenTreeData(renderTreeData.value).find((item) => item.id === id);
      // 当前筛选下没有这个节点就不动高亮
      if (node) {
        selectTreeNode(node);
      }
    },
    setStatus(value: string) {
      statusValue.value = value;
    },
  });
</script>
<style lang="less">
  .search-tree-main {
    display: flex;
    width: 100%;
    height: 100%;
    padding: 0 12px;
    background-color: #fff;
    flex-direction: column;

    .search-input {
      min-height: 32px;
      margin-top: 8px;
      margin-bottom: 8px;
    }

    .status-select-main {
      display: flex;
      width: 100%;
      min-height: 32px;
      overflow: hidden;

      .select-title {
        display: flex;
        width: 64px;
        height: 32px;
        min-width: 64px;
        font-size: 12px;
        color: #4d4f56;
        background: #eaebf0;
        border-radius: 2px 0 0 2px;
        align-items: center;
        justify-content: center;
      }

      .bk-select {
        overflow: hidden;
        cursor: pointer;
        flex: 1;

        .select-result-display {
          display: flex;
          height: 32px;
          padding: 0 8px;
          background: #f0f1f5;
          align-items: center;
          border: 1px solid #f0f1f5;

          &:hover {
            border-color: #979ba5 !important;
          }

          .display-txt {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .arrow-icon {
            margin-left: auto;
            font-size: 14px;
            color: #979ba5;
          }
        }
      }
    }

    .flow-tree-main {
      height: auto !important;

      .task-detail-tree-node {
        display: flex;
        width: 100%;
        align-items: center;
        padding-right: 12px;

        &:hover {
          background-color: #f0f1f5;

          .view-log-main {
            display: block;
          }
        }

        &.is-sub-process {
          .flow-sign-icon-main {
            margin-right: 6px;
          }
        }

        .view-log-main {
          display: none;
        }

        .node-name {
          flex: 1;
          font-size: 12px;
        }
      }

      .node-check-box {
        margin-right: 12px;
      }
    }
  }
</style>
