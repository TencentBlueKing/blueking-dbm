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
  <BkResizeLayout
    :border="false"
    class="database-content"
    collapsible
    initial-divide="312px"
    :max="500"
    :min="312">
    <template #aside>
      <BkLoading
        :loading="treeState.loading"
        style="height: 100%;"
        :z-index="12">
        <div class="content-tree">
          <BkInput
            v-model="treeState.search"
            class="content-tree__search"
            :placeholder="$t('请输入节点名称')"
            type="search" />
          <BkTree
            ref="treeRef"
            class="db-scroll-y"
            :data="treeState.data"
            :indent="16"
            label="name"
            :node-content-action="['click']"
            node-key="treeId"
            :offset-left="24"
            :prefix-icon="treePrefixIcon"
            :search="treeSearchConfig"
            :selected="treeState.selected"
            @node-click="handleSelectedTreeNode">
            <template #node="item">
              <div class="content-tree__node">
                <span class="content-tree__tag">
                  {{ getIconText(item) }}
                </span>
                <span
                  v-overflow-tips="{ content:item.name, placement: 'right' }"
                  class="content-tree__name text-overflow">
                  {{ item.name }}
                </span>
                <i
                  v-if="hasModules && item.levelType === ConfLevels.APP"
                  v-bk-tooltips="$t('新建DB模块')"
                  class="content-tree__add db-icon-add"
                  @click.stop="createModule" />
                <!-- <span class="content-tree__count">{{item.count}}</span>
                  <span v-if="item.version" class="content-tree__version">{{item.version}}</span> -->
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
    <template #main>
      <div
        v-if="treeState.activeNode"
        :key="treeState.activeNode.id"
        class="content-details">
        <div class="content-details__title">
          <strong class="content-details__title-name">{{ treeState.activeNode.name }}</strong>
          <BkTag theme="info">
            {{ treeState.activeNode.tag }}
          </BkTag>
          <BkTag v-if="treeState.activeNode.version">
            {{ treeState.activeNode.version }}
          </BkTag>
        </div>
        <Component :is="activeComponent" />
      </div>
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import { clusterTypeInfos, ClusterTypes, type ClusterTypesValues, ConfLevels } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import ConfigBusiness from './biz/ConfigInfo.vue';
  import ConfigCluster from './cluster/ConfigInfo.vue';
  import type { TreeData, TreeState } from './common/types';
  import { useTreeData } from './hooks/useTreeData';
  import ConfigModule from './module/ConfigInfo.vue';

  const route = useRoute();
  const treeState = reactive<TreeState>({
    isAnomalies: false,
    loading: false,
    search: '',
    data: [],
  });
  const {
    treeRef,
    treeSearchConfig,
    treePrefixIcon,
    handleSelectedTreeNode,
    createModule,
    fetchBusinessTopoTree,
  } = useTreeData(treeState);
  // 可创建模块
  const clusterType = computed(() => route.params.clusterType as string);
  const hasModuleClusters: string[] = [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA];
  const hasModules = computed(() => hasModuleClusters.includes(clusterType.value));

  const getIconText = (item: TreeData) => {
    if (item.levelType === ConfLevels.APP) return '业';
    if (item.levelType === ConfLevels.MODULE) return '模';
    return '集';
  };

  /**
   * content component
   */
  const activeComponent = computed(() => {
    if (!treeState.activeNode) return '';

    const { levelType } = treeState.activeNode;

    if (levelType === ConfLevels.APP) return ConfigBusiness;

    if (levelType === ConfLevels.MODULE) return ConfigModule;

    if (levelType === ConfLevels.CLUSTER) return ConfigCluster;

    return '';
  });

  const handleClearSearch = () => {
    treeState.search = '';
  };

  const handleRefresh = () => {
    const { dbType } = clusterTypeInfos[clusterType.value as ClusterTypesValues];
    dbType && fetchBusinessTopoTree(dbType);
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .database-content {
    height: 100%;

    :deep(.bk-resize-layout-aside) {
      &::after {
        display: none;
      }
    }
  }

  .content-tree {
    height: 100%;
    padding: 16px 0;

    .bk-tree {
      height: calc(100% - 42px);
      font-size: 12px;

      :deep(.bk-node-prefix) {
        color: #979ba5;
      }

      :deep(.bk-node-row) {
        &:hover {
          background-color: #e1ecff;
        }
      }
    }

    &__node {
      .flex-center();

      padding: 0 16px 0 4px;
    }

    &__tag {
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

    &__name {
      flex: 1;
      margin-right: 4px;
    }

    &__add {
      display: none;
      margin-right: 4px;
    }

    &__count,
    &__version {
      padding: 0 6px;
      margin-left: 4px;
      line-height: 16px;
      color: @gray-color;
      background-color: @bg-dark-gray;
      border-radius: 2px;
    }

    :deep(.bk-node-row) {
      &.is-selected {
        color: @primary-color;
        background-color: #e1ecff;

        .bk-node-prefix {
          color: #3a84ff;
        }

        .content-tree__add {
          display: block;
        }

        .content-tree__tag {
          background-color: #3a84ff;
        }

        .content-tree__count,
        .content-tree__version {
          color: @white-color;
          background-color: #a3c5fd;
        }
      }

      &:hover {
        .content-tree__add {
          display: block;
        }
      }
    }

    &__search {
      display: flex;
      width: 280px;
      margin: 0 auto 12px;
      background: @bg-white;
    }
  }

  .content-details {
    height: 100%;
    padding: 24px;
    background-color: @bg-white;

    &__title {
      padding-bottom: 16px;

      &-name {
        padding: 0 8px 0 4px;
        color: @title-color;
      }
    }
  }
</style>
