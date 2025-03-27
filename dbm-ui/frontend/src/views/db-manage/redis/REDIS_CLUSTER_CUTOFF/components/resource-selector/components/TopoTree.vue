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
    class="resource-selector-topo-tree"
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
        :selected="selectNode"
        :show-node-type-icon="false"
        virtual-render
        @node-click="handleNodeClick">
        <template #node="item">
          <div class="custom-tree-node">
            <span class="custom-tree-node-tag">
              {{ item.obj === 'biz' ? '业' : '集' }}
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

  import { getRedisList } from '@services/source/redis';

  import { useGlobalBizs } from '@stores';

  export interface TopoTreeNode {
    children?: TopoTreeNode[];
    clusterInfo?: ServiceReturnType<typeof getRedisList>['results'][0];
    count: number;
    id: number;
    name: string;
    obj: 'biz' | 'cluster';
  }

  const selectNode = defineModel<TopoTreeNode>();

  const { t } = useI18n();
  const { currentBizId, currentBizInfo } = useGlobalBizs();

  const treeSearch = ref('');
  const treeRef = ref();
  const treeData = shallowRef<TopoTreeNode[]>([]);

  const { loading } = useRequest(getRedisList, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
      },
    ],
    onSuccess(data) {
      let total = 0;
      const clusterIds: number[] = [];
      const children = data.results.reduce<TopoTreeNode[]>((acc, cluster) => {
        total += cluster.count;
        clusterIds.push(cluster.id);
        return [
          ...acc,
          {
            clusterInfo: cluster,
            count: cluster.count,
            id: cluster.id,
            name: cluster.master_domain,
            obj: 'cluster',
          },
        ];
      }, []);
      treeData.value = [
        {
          children,
          count: total,
          id: currentBizId,
          name: currentBizInfo?.display_name || '--',
          obj: 'biz',
        },
      ];
      setTimeout(() => {
        if (data.results.length > 0) {
          [selectNode.value] = treeData.value;
          const [firstRawNode] = treeRef.value.getData().data;
          treeRef.value.setOpen(firstRawNode);
          treeRef.value.setSelect(firstRawNode);
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
    const rawNode = treeRef.value.getData().data.find((item: { id: number }) => item.id === node.id);
    selectNode.value = node;
    if (!isOpen && !isSelected) {
      treeRef.value.setNodeOpened(rawNode, true);
      treeRef.value.setSelect(rawNode, true);
      return;
    }

    if (isOpen && !isSelected) {
      treeRef.value.setSelect(rawNode, true);
      return;
    }

    if (isSelected) {
      treeRef.value.setNodeOpened(rawNode, !isOpen);
    }
  };
</script>
<style lang="less">
  .resource-selector-topo-tree {
    height: 570px;
    padding: 24px;

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
