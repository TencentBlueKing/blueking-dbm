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
  <div class="operation-record">
    <DbQuickSearch
      v-model="searchValue"
      class="mb-16"
      :data="quickSearchData"
      :placeholder="t('搜索操作人_操作时间_配置名称_参数类型_操作类型_参数名')"
      style="width: 500px"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      fixed-pagination
      row-key="id"
      @clear-search="handleQuickSearchChange">
      <TableColumn
        col-key="op_user"
        :title="t('操作人')"
        :width="140">
        <template #default="{ row }">
          {{ row.op_user || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updated_at"
        :title="t('操作时间')"
        :width="220">
        <template #default="{ row }">
          {{ row.updated_at || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_file_lc"
        ellipsis
        :title="t('配置文件')">
        <template #default="{ row }">
          {{ row.conf_file_lc || '--' }}
        </template>
      </TableColumn>
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
      <TableColumn
        col-key="conf_name"
        ellipsis
        :title="t('操作参数')">
        <template #default="{ row }">
          {{ row.conf_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_value"
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
            <span class="config-change-value__before">{{ row.before_image?.conf_value }}</span>
            <span class="config-change-value__icon">
              <DbIcon
                size="small"
                type="bk-dbm-icon db-icon-arrow-right" />
            </span>
            <span class="config-change-value__after">{{ row.after_image?.conf_value }}</span>
          </span>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getConfigItemChanges } from '@services/source/configs';

  import DbTable from '@components/db-table/IndexNew.vue';

  const { t } = useI18n();
  const activeClusterType = inject<Ref<string>>('activeClusterType');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

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
      id: 'conf_name',
      name: t('配置名称'),
      type: 'input' as const,
    },
    {
      id: 'conf_type',
      name: t('配置类型'),
      type: 'input' as const,
    },
    {
      id: 'operate_type',
      name: t('操作类型'),
      type: 'input' as const,
    },
    {
      id: 'operate_param',
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
    if (!activeClusterType?.value) {
      return { count: 0, results: [] };
    }
    const res = await getConfigItemChanges({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      namespace: activeClusterType.value,
    });

    // 前端过滤
    let filteredData = res.results || [];
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
</script>

<style lang="less" scoped>
  .operation-record {
    padding: 0 16px;
  }

  .config-change-value {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    position: relative;

    &.is-add {
      color: #2caf5e;
    }

    &__before {
      color: #f59500;
      flex-shrink: 1;
      max-width: 45%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &__icon {
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

    &__after {
      color: #2caf5e;
      flex-shrink: 1;
      max-width: 45%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
