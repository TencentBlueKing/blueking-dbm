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
        <DbQuickSearch
          v-model="treeSearchValue"
          :data="searchSelectData" />
      </div>
      <BkTree
        ref="treeRef"
        :data="displayTreeData"
        :indent="0"
        label="name"
        :line-height="48"
        :node-content-action="['click']"
        node-key="treeId"
        :offset-left="8"
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
            <div class="config-tree-text">
              <span
                v-overflow-tips="{ content: item.name, placement: 'right' }"
                class="config-tree-name text-overflow">
                {{ item.name }}
              </span>
              <!-- 模块节点第二行：`${存储层系列}，${字符集}` -->
              <span
                v-if="item.levelType === ConfLevels.MODULE && item.subDescription"
                v-overflow-tips="{ content: item.subDescription, placement: 'right' }"
                class="config-tree-desc text-overflow">
                {{ item.subDescription }}
              </span>
            </div>
            <!-- 模块节点右端：关联集群数（灰底小方块，≥1000 显示 999+，纯展示） -->
            <span
              v-if="item.levelType === ConfLevels.MODULE"
              class="cluster-count-tag">
              {{ formatClusterCount(item.clusters?.length ?? 0) }}
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
            :is-searching="isSearching"
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
  import type { Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
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

  const {
    charsetOptions,
    createModule,
    fetchBusinessTopoTree,
    filterTreeBySearch,
    handleSelectedTreeNode,
    treePrefixIcon,
    treeRef,
    treeSearchConfig,
    treeSearchValue,
  } = useTreeData(treeState);

  // 默认按模块名搜索，字符集候选取当前树数据去重结果
  const searchSelectData = computed<QuickSearchProps['data']>(() => [
    {
      default: true,
      id: 'moduleName',
      name: t('模块名'),
      type: 'input',
    },
    {
      id: 'moduleId',
      name: t('模块 ID'),
      type: 'input',
    },
    {
      id: 'charset',
      list: charsetOptions.value.map((item) => ({
        label: item,
        value: item,
      })),
      name: t('字符集'),
      type: 'multiple',
    },
  ]);

  /** 应用分字段过滤后的树数据 */
  const displayTreeData = computed(() => filterTreeBySearch(treeState.data));

  /** 是否处于搜索态（含原关键字搜索与分字段条件） */
  const isSearching = computed(() => Boolean(treeState.search) || Object.values(treeSearchValue.value).some(Boolean));

  /** 关联集群数：≥1000 显示 999+（口径同详情，纯展示） */
  const formatClusterCount = (count: number) => (count >= 1000 ? '999+' : String(count));

  const handleClearSearch = () => {
    treeState.search = '';
    treeSearchValue.value = {};
  };

  const handleRefresh = () => {
    const { dbType } = clusterTypeInfos[clusterType.value as ClusterTypes];
    if (dbType) {
      fetchBusinessTopoTree(dbType);
    }
  };

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

  defineExpose({
    handleRefresh,
    treeState,
  });
</script>

<style lang="less" scoped>
  .config-tree {
    display: flex;
    height: 100%;
    min-width: 0;
    padding: 16px;
    background-color: @bg-white;
    flex-direction: column;
    gap: 16px;

    .config-tree-search {
      flex-shrink: 0;
    }

    /* 行与搜索框左右对齐（设计源：同为 16px 内缩、等宽）；预留滚动条宽度，
       行内容不再被滚动条压住；overflow: clip 防止行底色横向溢出到侧栏之外 */
    :deep(.bk-tree) {
      min-width: 0;
      min-height: 0;
      overflow: clip;
      flex: 1;
      font-size: 12px;

      .bk-tree-container {
        overflow: auto;
        scrollbar-gutter: stable;
      }

      /* 设计稿行内边距 8px；展开箭头占位（node-action）补足到名称起点 */
      .bk-node-row {
        padding-right: 8px;
      }

      .bk-node-prefix {
        width: 12px;
        height: 12px;
        color: #3a84ff;
      }

      .bk-node-action {
        width: 12px;
        margin-right: 8px;
        color: #3a84ff;
      }
    }

    .config-tree-node {
      display: flex;
      width: 100%;
      min-width: 0;
      align-items: center;
    }

    /* 模块名与第二行描述左对齐，整列作为节点正文区 */
    .config-tree-text {
      display: flex;
      min-width: 0;
      flex: 1;
      flex-direction: column;
      justify-content: center;
    }

    .config-tree-name {
      font-size: 12px;
      line-height: 20px;
      color: #4d4f56;
    }

    .config-tree-desc {
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
    }

    .config-tree-tag {
      width: 24px;
      height: 24px;
      margin-right: 8px;
      font-size: 12px;
      line-height: 24px;
      color: white;
      text-align: center;
      background-color: #c4c6cc;
      flex-shrink: 0;
      border-radius: 50%;
    }

    .cluster-count-tag {
      height: 18px;
      padding: 0 8px;
      margin-left: 8px;
      font-size: 12px;
      line-height: 18px;
      color: #4d4f56;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
      flex-shrink: 0;
    }

    .config-tree-add-btn {
      display: flex;
      width: 26px;
      height: 26px;
      min-width: 26px;
      padding: 5px;
      margin-left: 8px;
      border-radius: 2px;
    }

    :deep(.bk-node-row) {
      &.is-selected {
        background-color: #e1ecff;

        .config-tree-name {
          color: @primary-color;
        }

        .config-tree-tag {
          background-color: #3a84ff;
        }
      }

    }
  }
</style>
