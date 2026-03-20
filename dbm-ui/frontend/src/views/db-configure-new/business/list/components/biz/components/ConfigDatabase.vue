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
  <DbTable
    ref="tableRef"
    :custom-sort-method="handleCustomSort"
    :data-source="dataSource"
    row-key="name"
    :sort="tableSort"
    @clear-search="refreshTable">
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
      :title="t('更新时间')">
      <template #default="{ row }">
        {{ row.updated_at ? utcDisplayTime(row.updated_at) : '--' }}
      </template>
    </TableColumn>
  </DbTable>
</template>

<script setup lang="ts">
  import type { TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getBusinessConfigList } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import DbTable from '@components/db-table/IndexNew.vue';

  import type { TreeData } from '@views/db-configure-new/common/types';

  import { utcDisplayTime } from '@/utils';
  import { saveConfigureState } from '@/views/db-configure-new/utils/configureState';

  type ConfigListItem = ServiceReturnType<typeof getBusinessConfigList>;

  interface Props {
    confType: string;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const activeClusterType = inject<Ref<string>>('activeClusterType');
  const treeNode = inject<Ref<TreeData>>('treeNode');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  // 受控排序状态（不默认排序，由用户点击表头触发）
  const tableSort = ref<TableSort | undefined>(undefined);

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

      // 按当前排序状态动态排序（自然序）
      if (tableSort.value) {
        const sortItem = Array.isArray(tableSort.value) ? tableSort.value[0] : tableSort.value;
        if (sortItem?.sortBy) {
          filteredData.sort((a, b) => {
            const valA = String((a as Record<string, any>)[sortItem.sortBy] ?? '');
            const valB = String((b as Record<string, any>)[sortItem.sortBy] ?? '');
            const compare = valA.localeCompare(valB, undefined, { numeric: true });
            return sortItem.descending ? -compare : compare;
          });
        }
      }
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

  const refreshTable = () => {
    tableRef.value?.fetchData({}, true);
  };

  /** 自定义排序方法：更新排序状态并重新拉取数据 */
  const handleCustomSort = (sort: TableSort) => {
    const sortItem = Array.isArray(sort) ? sort[0] : sort;
    if (sortItem?.sortBy) {
      tableSort.value = { descending: sortItem.descending, sortBy: sortItem.sortBy };
    } else {
      tableSort.value = undefined;
    }
    refreshTable();
  };

  /** 查看详情 */
  const handleToDetails = (row: ConfigListItem[number]) => {
    // 保存当前状态到 sessionStorage（返回时自动恢复）
    saveConfigureState({
      activeTab: props.confType,
      selectedParentId: treeNode?.value?.parentId,
      selectedTreeId: treeNode?.value?.treeId,
    });

    router.push({
      name: 'DbConfigureDetail',
      params: {
        clusterType: activeClusterType?.value,
        confType: props.confType,
        version: row.version,
      },
    });
  };

  onMounted(() => {
    refreshTable();
  });
</script>
