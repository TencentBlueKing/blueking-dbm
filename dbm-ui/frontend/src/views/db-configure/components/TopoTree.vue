<!--
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
-->

<template>
  <BkLoading
    :loading="treeState.loading"
    style="height: 100%"
    :z-index="12">
    <div class="config-tree">
      <div class="config-tree-search">
        <BkInput
          v-model="treeState.search"
          :placeholder="t('请输入模块名')"
          type="search" />
      </div>
      <BkTree
        ref="treeRef"
        :data="treeState.data"
        :indent="16"
        label="name"
        :node-content-action="['click']"
        node-key="treeId"
        :offset-left="24"
        :prefix-icon="treePrefixIcon"
        :search="treeSearchConfig"
        :selected="treeState.selected"
        virtual-render
        @node-click="handleSelectedTreeNode">
        <template #node="item">
          <div class="config-tree-node">
            <span class="config-tree-tag">
              {{ getIconText(item) }}
            </span>
            <span
              v-overflow-tips="{ content: item.name, placement: 'right' }"
              class="config-tree-name text-overflow">
              {{ item.name }}
            </span>
            <AuthButton
              v-if="item.levelType === ConfLevels.APP && isShowAddBtn"
              v-bk-tooltips="t('新建DB模块')"
              action-id="dbconfig_edit"
              class="config-tree-add-btn"
              :resource="dbType"
              size="small"
              theme="primary"
              @click.stop="createModule">
              <DbIcon type="add" />
            </AuthButton>
          </div>
        </template>
        <template #empty>
          <EmptyStatus
            :is-anomalies="treeState.isAnomalies"
            :is-searching="!!treeState.search"
            @clear-search="handleClearSearch"
            @refresh="handleRefresh" />
        </template>
      </BkTree>
    </div>
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { clusterTypeInfos, ClusterTypes, ConfLevels, DBTypes } from '@common/const';

  import AuthButton from '@components/auth-component/button.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import type { TreeData, TreeState } from '@views/db-configure/common/types';
  import { useTreeData } from '@views/db-configure/hooks/useTreeData';

  const route = useRoute();
  const { t } = useI18n();

  const treeState = reactive<TreeState>({
    data: [],
    isAnomalies: false,
    loading: false,
    search: '',
  });

  const { createModule, fetchBusinessTopoTree, handleSelectedTreeNode, treePrefixIcon, treeRef, treeSearchConfig } =
    useTreeData(treeState);

  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);
  const dbType = computed(() => clusterTypeInfos[clusterType.value as ClusterTypes]?.dbType || DBTypes.MYSQL);

  const isShowAddBtn = computed(() => {
    return dbType.value ? [DBTypes.MYSQL, DBTypes.SQLSERVER, DBTypes.TENDBCLUSTER].includes(dbType.value) : false;
  });

  const getIconText = (item: TreeData) => {
    if (item.levelType === ConfLevels.APP) {
      return '业';
    }
    if (item.levelType === ConfLevels.MODULE) {
      return '模';
    }
    return '集';
  };

  const handleClearSearch = () => {
    treeState.search = '';
  };

  const handleRefresh = () => {
    const { dbType } = clusterTypeInfos[clusterType.value as ClusterTypes];
    if (dbType) {
      fetchBusinessTopoTree(dbType);
    }
  };

  defineExpose({
    handleRefresh,
    treeState,
  });
</script>

<style lang="less" scoped>
  .config-tree {
    height: 100%;
    padding: 16px;
    background-color: @bg-white;

    .bk-tree {
      height: calc(100% - 42px) !important;
      font-size: 12px;

      :deep(.bk-node-prefix) {
        color: #979ba5;
      }

      :deep(.bk-node-row) {
        padding-left: 8px;

        &:hover {
          background-color: #e1ecff;
        }
      }
    }

    .config-tree-node {
      display: flex;
      align-items: center;
      padding: 0 4px;
    }

    .config-tree-tag {
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

    .config-tree-name {
      flex: 1;
      margin-right: 4px;
    }

    .config-tree-add-btn {
      display: none;
      width: 26px;
      height: 26px;
      min-width: 26px;
      padding: 5px;
      border-radius: 2px;
    }

    :deep(.bk-node-row) {
      &.is-selected {
        color: @primary-color;
        background-color: #e1ecff;

        .bk-node-prefix {
          color: #3a84ff;
        }

        .config-tree-add-btn {
          display: flex;
        }

        .config-tree-tag {
          background-color: #3a84ff;
        }
      }

      &:hover {
        .config-tree-add-btn {
          display: flex;
        }
      }
    }

    .config-tree-search {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
