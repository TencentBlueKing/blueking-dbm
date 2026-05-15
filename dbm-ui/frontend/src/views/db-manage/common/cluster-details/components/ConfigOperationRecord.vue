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
  <div class="cluster-config-operation-record">
    <DbQuickSearch
      v-model="searchValue"
      class="mb-16"
      :data="quickSearchData"
      :placeholder="t('搜索操作人_操作时间_配置类型_配置文件_操作类型_操作参数')"
      style="width: 500px"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="tableRef"
      :custom-sort-method="handleCustomSort"
      :data-source="dataSource"
      fixed-pagination
      row-key="id"
      :sort="tableSort"
      @clear-search="handleQuickSearchChange">
      <!-- 1. 操作时间 -->
      <TableColumn
        col-key="updated_at"
        sorter
        :title="t('操作时间')"
        :width="220">
        <template #default="{ row }">
          {{ row.updated_at || '--' }}
        </template>
      </TableColumn>
      <!-- 2. 操作人 -->
      <TableColumn
        col-key="op_user"
        :title="t('操作人')"
        :width="140">
        <template #default="{ row }">
          {{ row.op_user || '--' }}
        </template>
      </TableColumn>
      <!-- 3. 配置类型 -->
      <TableColumn
        col-key="conf_type_lc"
        :title="t('配置类型')"
        :width="120">
        <template #default="{ row }">
          <BkTag>
            {{ row.conf_type_lc }}
          </BkTag>
        </template>
      </TableColumn>
      <!-- 4. 配置文件 -->
      <TableColumn
        col-key="conf_file_lc"
        ellipsis
        :title="t('配置文件')">
        <template #default="{ row }">
          {{ row.conf_file_lc || '--' }}
        </template>
      </TableColumn>
      <!-- 5. 操作类型 -->
      <TableColumn
        col-key="op_type"
        :title="t('操作类型')"
        :width="120">
        <template #default="{ row }">
          <BkTag :theme="operateTypeThemeMap[row.op_type]?.theme || ''">
            {{ operateTypeThemeMap[row.op_type]?.text || '--' }}
          </BkTag>
        </template>
      </TableColumn>
      <!-- 6. 操作参数 -->
      <TableColumn
        col-key="conf_name"
        ellipsis
        :title="t('操作参数')"
        :width="200">
        <template #default="{ row }">
          {{ row.conf_name || '--' }}
        </template>
      </TableColumn>
      <!-- 7. 操作明细 -->
      <TableColumn
        col-key="conf_value"
        :min-width="200"
        :title="t('操作明细')">
        <template #default="{ row }">
          <span
            v-if="!row.before_image?.conf_value"
            class="config-change-value is-add">
            {{ row.after_image?.conf_value || t('无') }}
          </span>
          <span
            v-else
            class="config-change-value">
            <span class="config-change-value-before">{{ row.before_image?.conf_value }}</span>
            <span class="config-change-value-icon">
              <DbIcon
                size="small"
                type="bk-dbm-icon db-icon-arrow-right" />
            </span>
            <span class="config-change-value-after">{{ row.after_image?.conf_value }}</span>
          </span>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import type { TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { getConfigItemChanges } from '@services/source/configs';

  import type { ClusterTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  // 受控排序状态
  const tableSort = ref<{ descending: boolean; sortBy: string }>({
    descending: true,
    sortBy: 'updated_at',
  });

  const quickSearchData = [
    {
      id: 'op_user',
      name: t('操作人'),
      type: 'input' as const,
    },
    {
      id: 'updated_at',
      name: t('操作时间'),
      type: 'input' as const,
    },
    {
      id: 'conf_type_lc',
      name: t('配置类型'),
      type: 'input' as const,
    },
    {
      id: 'conf_file_lc',
      name: t('配置文件'),
      type: 'input' as const,
    },
    {
      id: 'op_type',
      name: t('操作类型'),
      type: 'input' as const,
    },
    {
      id: 'conf_name',
      name: t('操作参数'),
      type: 'input' as const,
    },
  ];

  type TagTheme = '' | 'danger' | 'info' | 'success' | 'warning';

  /** 操作类型标签主题映射 */
  const operateTypeThemeMap: Record<
    string,
    {
      text: string;
      theme: TagTheme;
    }
  > = {
    add: {
      text: t('新增参数'),
      theme: 'success',
    },
    recover: {
      text: t('恢复默认'),
      theme: 'info',
    },
    remove: {
      text: t('删除参数'),
      theme: 'danger',
    },
    update: {
      text: t('修改参数'),
      theme: 'warning',
    },
    upsert: {
      text: t('新增参数'),
      theme: 'success',
    },
  };

  /** 数据源函数 - 适配 DbTable 组件 */
  const dataSource = async (params: { limit: number; offset: number }) => {
    const res = await getConfigItemChanges({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      level_name: 'cluster',
      level_value: props.cluster.master_domain,
      namespace: props.cluster.cluster_type,
    });

    // 前端过滤
    let filteredData = res.results || [];

    // 按当前排序状态动态排序
    filteredData.sort((a, b) => {
      const valA = String((a as Record<string, any>)[tableSort.value.sortBy] ?? '');
      const valB = String((b as Record<string, any>)[tableSort.value.sortBy] ?? '');
      return tableSort.value.descending ? valB.localeCompare(valA) : valA.localeCompare(valB);
    });

    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      filteredData = filteredData.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          const search = String(val).toLowerCase();
          const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    // 前端分页
    const start = params.offset;
    const end = start + params.limit;
    return {
      count: filteredData.length,
      results: filteredData.slice(start, end),
    };
  };

  const handleQuickSearchChange = () => {
    tableRef.value?.fetchData({}, true);
  };

  /** 自定义排序方法：更新排序状态并重新拉取数据 */
  const handleCustomSort = (sort: TableSort) => {
    if (!Array.isArray(sort) && sort?.sortBy) {
      tableSort.value = { descending: sort.descending, sortBy: sort.sortBy };
    }
    tableRef.value?.fetchData({}, true);
  };
</script>

<style lang="less" scoped>
  .cluster-config-operation-record {
    padding: 0 16px;

    .config-change-value {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      position: relative;

      &.is-add {
        color: #2caf5e;
      }

      &-before {
        color: #f59500;
        flex-shrink: 1;
        white-space: nowrap;
      }

      &-icon {
        color: #979ba5;
        display: flex;
        flex-shrink: 0;
        width: 14px;
        height: 14px;
        padding: 2px;
        justify-content: center;
        align-items: center;
        gap: 10px;
        aspect-ratio: 1 / 1;
        border-radius: 999px;
        background: var(--Neutral-8--, #f0f1f5);
      }

      &-after {
        color: #2caf5e;
        flex-shrink: 1;
        white-space: nowrap;
      }
    }
  }
</style>
