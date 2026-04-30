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
  <div class="biz-database">
    <div class="biz-database-operations mb-16">
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        :placeholder="t('搜索配置名称_配置文件_更新人_描述')"
        style="width: 500px"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :custom-sort-method="handleCustomSort"
      :data-source="dataSource"
      row-key="name"
      :sort="tableSort"
      @clear-search="handleQuickSearchChange">
      <TableColumn
        col-key="name"
        ellipsis
        :title="t('配置名称')">
        <template #default="{ row }">
          <BkButton
            text
            theme="primary"
            @click="handleToDetails(row)">
            {{ row.name }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="version"
        ellipsis
        :title="t('配置文件')" />
      <TableColumn
        col-key="description"
        ellipsis
        :title="t('描述')">
        <template #default="{ row }">
          {{ row.description || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updated_by"
        :title="t('更新人')">
        <template #default="{ row }">
          {{ row.updated_by || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updated_at"
        sorter
        :title="t('更新时间')" />
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import type { TableSort } from 'tdesign-vue-next';
  import type { ComputedRef, Ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import { getBusinessConfigList } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import DbTable from '@components/db-table/IndexNew.vue';

  import type { TreeData } from '@views/db-configure-new/common/types';

  type ConfigListItem = ServiceReturnType<typeof getBusinessConfigList>;

  interface Props {
    confType: string;
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const activeClusterType = inject<Ref<string>>('activeClusterType');
  const treeNode = inject<ComputedRef<TreeData>>('treeNode');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  // 受控排序状态
  const tableSort = ref<{ descending: boolean; sortBy: string }>({
    descending: true,
    sortBy: 'updated_at',
  });

  const quickSearchData = [
    {
      id: 'name',
      name: t('配置名称'),
      type: 'input' as const,
    },
    {
      id: 'version',
      name: t('配置文件'),
      type: 'input' as const,
    },
    {
      id: 'description',
      name: t('描述'),
      type: 'input' as const,
    },
    {
      id: 'updated_by',
      name: t('更新人'),
      type: 'input' as const,
    },
    {
      id: 'updated_at',
      name: t('更新时间'),
      type: 'input' as const,
    },
  ];

  /** 数据源函数 - 适配 DbTable 组件 */
  const dataSource = (params: { limit: number; offset: number }) => {
    if (!activeClusterType?.value) {
      return Promise.resolve({ count: 0, results: [] });
    }
    return getBusinessConfigList(
      {
        bk_biz_id: globalBizsStore.currentBizId,
        conf_type: props.confType,
        limit: -1,
        meta_cluster_type: activeClusterType.value,
      },
      { permission: 'catch' },
    ).then((res) => {
      // 前端过滤
      let filteredData = res;

      // 按当前排序状态动态排序
      filteredData.sort((a, b) => {
        const valA = String((a as Record<string, any>)[tableSort.value.sortBy] ?? '');
        const valB = String((b as Record<string, any>)[tableSort.value.sortBy] ?? '');
        return tableSort.value.descending ? valB.localeCompare(valA) : valA.localeCompare(valB);
      });
      const filters = searchValue.value;
      if (Object.keys(filters).length > 0) {
        filteredData = res.filter((item) => {
          const row = item as { description?: string } & ConfigListItem[number];
          return Object.entries(filters).every(([key, val]) => {
            if (!val) return true;
            const search = String(val).toLowerCase();
            const fieldValue = String((row as Record<string, any>)[key] ?? '').toLowerCase();
            return fieldValue.includes(search);
          });
        });
      }
      // 前端分页
      const start = params.offset;
      const end = start + params.limit;
      return {
        count: filteredData.length,
        results: filteredData.slice(start, end),
      };
    });
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

  /** 查看详情 */
  const handleToDetails = (row: ConfigListItem[number]) => {
    router.push({
      name: 'DbConfigureDetail',
      params: {
        clusterType: activeClusterType?.value,
        confType: props.confType,
        parentId: treeNode?.value?.parentId || undefined,
        treeId: treeNode?.value?.treeId || undefined,
        version: row.version,
      },
      query: {
        from: route.name as string,
      },
    });
  };
</script>

<style lang="less" scoped>
  .biz-database {
    padding: 0 16px;
  }
</style>
