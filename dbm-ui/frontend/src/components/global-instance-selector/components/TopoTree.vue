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
  <BkLoading
    class="global-instance-selector-topo-tree"
    :loading="loading">
    <BkInput
      v-model="treeSearch"
      clearable
      :placeholder="t('搜索拓扑节点')" />
    <div class="topo-tree-box">
      <BkTree
        ref="treeRef"
        children="children"
        :data="treeData"
        label="name"
        :node-content-action="['click']"
        :search="treeSearch"
        selectable
        :selected="selectedTreeNode"
        :show-node-type-icon="false"
        virtual-render
        @node-click="handleNodeClick">
        <template #node="item">
          <div
            class="custom-tree-node"
            :class="{
              'is-leaf': !item.children,
            }">
            <span
              v-if="item.nodeType"
              class="custom-tree-node-tag">
              {{ item.nodeType === 'biz' ? t('业') : t('模') }}
            </span>
            <span
              v-overflow-tips
              class="custom-tree-node-name text-overflow">
              {{ item.name }}
            </span>
            <span class="custom-tree-node-count">
              {{ item.count }}
            </span>
          </div>
        </template>
      </BkTree>
    </div>
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizModuleTopoTree } from '@services/source/cmdb';

  interface TopoTreeNode {
    children?: TopoTreeNode[];
    count: number;
    id: number;
    name: string;
    nodeType: 'biz' | 'module' | 'all';
    parentId?: number;
  }

  interface Props {
    params: ServiceParameters<typeof getBizModuleTopoTree>;
  }

  type Emits = (
    e: 'change',
    params: {
      bk_biz_id?: number;
      db_module_id?: number;
    },
  ) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const treeSearch = ref('');
  const treeRef = ref();
  const treeData = shallowRef<TopoTreeNode[]>([]);
  const selectedTreeNode = ref<TopoTreeNode>();

  const { loading } = useRequest(getBizModuleTopoTree, {
    defaultParams: [
      {
        cluster_type: props.params.cluster_type,
        count_type: 'instance',
        role: props.params.role,
      },
    ],
    onSuccess(data) {
      let count = 0;
      const children = data.reduce<TopoTreeNode[]>((acc, biz) => {
        count += biz.count;
        acc.push({
          children: biz.modules.map((module) => ({
            count: module.count,
            id: module.module_id,
            name: module.module_name,
            nodeType: 'module',
            parentId: biz.bk_biz_id,
          })),
          count: biz.count,
          id: biz.bk_biz_id,
          name: biz.bk_biz_name,
          nodeType: 'biz',
        });
        return acc;
      }, []);
      treeData.value = [
        {
          children,
          count,
          id: 0,
          name: t('全部'),
          nodeType: 'all',
        },
      ];
      setTimeout(() => {
        if (data.length > 0) {
          const [firstNode] = treeData.value;
          selectedTreeNode.value = firstNode;
        }
      });
    },
  });

  // 选中topo节点，获取topo节点下面的所有主机
  const handleNodeClick = (
    node: TopoTreeNode,
    {
      __is_open: isOpen,
      __is_selected: isSelected,
    }: {
      __is_open: boolean;
      __is_selected: boolean;
    },
  ) => {
    if (node.nodeType === 'biz') {
      emits('change', {
        bk_biz_id: node.id,
      });
    } else if (node.nodeType === 'module') {
      emits('change', {
        bk_biz_id: node.parentId,
        db_module_id: node.id,
      });
    } else {
      emits('change', {
        bk_biz_id: undefined,
        db_module_id: undefined,
      });
    }

    if (!isOpen && !isSelected) {
      treeRef.value.setNodeOpened(node, true);
      treeRef.value.setSelect(node, true);
      return;
    }

    if (isOpen && !isSelected) {
      treeRef.value.setSelect(node, true);
      return;
    }

    if (isSelected) {
      treeRef.value.setNodeOpened(node, !isOpen);
    }
  };
</script>
<style lang="less">
  .global-instance-selector-topo-tree {
    height: 570px;
    padding: 0 16px;

    .topo-tree-box {
      height: calc(100% - 95px);
      margin-top: 12px;
    }

    .bk-tree {
      .bk-node-content {
        font-size: 12px;
      }

      .bk-node-prefix {
        width: 12px !important;
        height: 12px !important;
        color: #979ba5;
      }

      .bk-node-row {
        .custom-tree-node {
          display: flex;
          align-items: center;

          .custom-tree-node-tag {
            width: 20px;
            height: 20px;
            margin-right: 8px;
            line-height: 20px;
            color: white;
            text-align: center;
            background-color: #c4c6cc;
            flex-shrink: 0;
            border-radius: 50%;
          }

          .custom-tree-node-name {
            flex: 1;
          }

          .custom-tree-node-count {
            height: 16px;
            padding: 0 6px;
            line-height: 16px;
            color: #979ba5;
            background-color: #f0f1f5;
            border-radius: 2px;
            flex-shrink: 0;
          }
        }

        .is-leaf {
          padding-left: 10px;
        }

        &.is-selected {
          color: @primary-color;
          background-color: #e1ecff;

          .custom-tree-node-tag {
            background-color: #3a84ff;
          }

          .custom-tree-node-count {
            color: white;
            background-color: #a3c5fd;
          }

          .bk-node-prefix {
            color: #3a84ff;
          }
        }
      }
    }
  }
</style>
