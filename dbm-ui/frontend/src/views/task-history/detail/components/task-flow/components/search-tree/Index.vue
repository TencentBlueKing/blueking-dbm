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
            <span>{{ statusDisplay }}</span>
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
      type="search"
      @clear="() => handleSearchChange('')"
      @enter="handleSearchChange" />
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
            :status="item.todoId ? 'TODO' : item.status"
            :type="item.type" />
          <span
            v-overflow-tips
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

  import { FlowTypes } from '@/services/source/taskflow';

  import { generateDifferentStatusTreeData, searchObj, type TreeNode } from '../flow-canvas/utils';

  import BatchOperation from './components/BatchOperation.vue';
  import FlowSign from './components/FlowSign.vue';
  import StatusSign from './components/StatusSign.vue';

  interface Props {
    data: TreeNode[];
    rootId: string;
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
    setStatus(value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

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

  const statusList = computed(() => {
    const allStatus = {
      count: 0,
      label: t('全部'),
      value: 'ALL',
    };
    const waitStatus = {
      count: 0,
      label: t('待执行'),
      value: 'CREATED',
    };
    const runningStatus = {
      count: 0,
      label: t('执行中'),
      value: 'RUNNING',
    };
    const successStatus = {
      count: 0,
      label: t('执行成功'),
      value: 'FINISHED',
    };
    const failedStatus = {
      count: 0,
      label: t('执行失败'),
      value: 'FAILED',
    };
    const todoStatus = {
      count: 0,
      label: t('待继续'),
      value: 'TODO',
    };

    const calcTreeData = (data: TreeNode[]) => {
      data.forEach((item) => {
        if (item.children) {
          calcTreeData(item.children);
        } else {
          if (item.status) {
            allStatus.count++;
          }
          if (item.status === 'FAILED') {
            failedStatus.count++;
          } else {
            if (item.todoId) {
              todoStatus.count++;
            } else {
              switch (item.status) {
                case 'CREATED':
                  waitStatus.count++;
                  break;
                case 'RUNNING':
                  runningStatus.count++;
                  break;
                case 'FINISHED':
                  successStatus.count++;
                  break;
              }
            }
          }
        }
      });
    };

    calcTreeData(props.data);

    const list = [allStatus, waitStatus, runningStatus, successStatus, failedStatus, todoStatus];
    list.forEach((item) => Object.assign(item, { label: `${item.label} ( ${item.count} )` }));
    return list;
  });

  const statusDisplay = computed(() => statusList.value.find((item) => item.value === statusValue.value)!.label);
  const showBatchOperation = computed(
    () => ['FAILED', 'RUNNING', 'TODO'].includes(statusValue.value) && renderTreeData.value.length,
  );

  const openedTreeNodesSet = new Set<string>();
  const checkedTreeNodesSet = new Set<string>();
  // 可展开父节点对应的全部子孙可展开id
  const treeIdChildrenMap: Record<string, Set<string>> = {};
  let currentClickNode = '';
  let isCheckedClick = false;
  // const isAutoFocus = false;

  const initTreeIdChildrenMap = (dataList: TreeNode[]) => {
    const deepInit = (list: TreeNode[]) => {
      list.forEach((item) => {
        if (item.children) {
          treeIdChildrenMap[item.id] = new Set<string>();
          item.children.forEach((child) => {
            if (child.children) {
              treeIdChildrenMap[item.id].add(child.id);
              deepInit(child.children);
            }
          });
          deepInit(item.children);
        }
      });
    };
    deepInit(dataList);

    const deepSetId = (parentId: string, idSet: Set<string>) => {
      idSet.forEach((item) => {
        if (treeIdChildrenMap[item]) {
          treeIdChildrenMap[parentId].add(item);
          if (treeIdChildrenMap[item].size) {
            deepSetId(parentId, treeIdChildrenMap[item]);
          }
        }
      });
    };

    Object.keys(treeIdChildrenMap).forEach((key) => {
      const children = treeIdChildrenMap[key];
      if (children.size) {
        deepSetId(key, children);
      }
    });
  };

  watch(treeSearch, () => {
    if (!treeSearch.value) {
      return;
    }

    batchSetTreeNodeOpen();
  });

  watch(statusValue, () => {
    if (statusValue.value !== 'ALL') {
      setTimeout(() => {
        // if (isAutoFocus) {
        //   return;
        // }

        // isAutoFocus = true;
        batchSetTreeNodeOpen();
        const firstLeafNode = findFirstLeafNode(renderTreeData.value)!;
        if (!firstLeafNode) {
          return;
        }

        treeRef.value!.setSelect(firstLeafNode);
        handleNodeClick(firstLeafNode);
      }, 500);
    }
  });

  // 恢复展开和点击状态
  watch(
    () => props.data,
    () => {
      setTimeout(() => {
        if (!Object.keys(treeIdChildrenMap).length) {
          initTreeIdChildrenMap(props.data);
        }

        if (treeSearch.value) {
          batchSetTreeNodeOpen();
        } else {
          const newTreeDataList = treeRef.value!.getData().data as TreeNode[];
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
        }
      });
    },
    {
      deep: true,
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

  const handleNodeCollapse = (node: TreeNode) => {
    // 收起时，已展开所有子孙都要跟着收起
    openedTreeNodesSet.delete(node.id);
    const childIds = treeIdChildrenMap[node.id];
    childIds.forEach((item) => {
      openedTreeNodesSet.delete(item);
    });
    if (node.pipeline) {
      emits('node-collapse', node);
    }
  };

  const handleSelectToggle = (isOpen: boolean) => {
    isSelectPanelOpen.value = isOpen;
  };

  const handleSearchChange = (value: string) => {
    if (!searchObj.key && !value) {
      return;
    }

    emits('search', value);
  };

  const handleNodeClick = (node: TreeNode) => {
    if (isCheckedClick) {
      isCheckedClick = false;
      return;
    }
    currentClickNode = node.id;
    const parentNodes: TreeNode[] = [];
    let parentNode = treeRef.value!.getParentNode(node);
    while (parentNode) {
      parentNodes.unshift(parentNode);
      parentNode = treeRef.value!.getParentNode(parentNode);
    }
    emits('node-click', node, parentNodes);
  };

  const handleNodeChecked = (list: TreeNode[]) => {
    isCheckedClick = true;
    checkedTreeNodesSet.clear();
    list.forEach((item) => checkedTreeNodesSet.add(item.id));
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

  defineExpose<Exposes>({
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

      .select-title {
        display: flex;
        width: 64px;
        height: 32px;
        font-size: 12px;
        color: #4d4f56;
        background: #eaebf0;
        border-radius: 2px 0 0 2px;
        align-items: center;
        justify-content: center;
      }

      .bk-select {
        flex: 1;
        cursor: pointer;

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
