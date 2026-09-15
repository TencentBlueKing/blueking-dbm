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
  <DbQuickSearch
    v-model="searchValue"
    class="cluster-selector-search"
    :data="searchSelectData"
    parse-url
    :placeholder="t('请输入或选择条件搜索')"
    @change="handleSearchChange" />
  <DbTable
    ref="tableRef"
    class="cluster-selector-table"
    :container-height="516"
    :data-source="getResourceList"
    disable-polling
    :disable-select-method="disableSelectMethod"
    :filter-value="searchValue"
    :row-class-name="getRowClass"
    row-click-selectable
    :row-key="tableConfig.rowKey ?? 'id'"
    :select-single="!multiple"
    selectable
    :selected="selected"
    @filter-change="handleFilterChange"
    @selection="handleSelection">
    <!-- 调用方传了 customColums 时整组替换标准列，列由调用方以数组给出，只能遍历渲染 -->
    <template v-if="customColumnList">
      <TableColumn
        v-for="column of customColumnList"
        :key="column.colKey"
        v-bind="column" />
    </template>
    <template v-else>
      <TableColumn
        col-key="master_domain"
        ellipsis
        fixed="left"
        :title="t('访问入口')"
        :width="280">
        <template #default="{ row }: { row: ResourceItem }">
          <TextOverflowLayout>
            {{ row.master_domain }}
            <template #append>
              <ClusterDetailRelatedTicket
                v-if="row.operations?.length"
                class="ml-4"
                :data="row.operations" />
              <BkTag
                v-if="row.isOffline"
                class="ml-4"
                size="small"
                theme="warning"
                type="stroke">
                {{ t('已禁用') }}
              </BkTag>
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="tag"
        :min-width="110"
        :title="t('标签')">
        <template #default="{ row }: { row: ResourceItem }">
          <TextOverflowLayout v-if="row.tags?.length">
            {{ row.tags.map((tag) => `${tag.key}: ${tag.value}`).join(' , ') }}
          </TextOverflowLayout>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="statusFilter"
        :min-width="100"
        :title="t('状态')">
        <template #default="{ row }: { row: ResourceItem }">
          <DbStatus :theme="isNormalStatus(row) ? 'success' : 'danger'">
            {{ isNormalStatus(row) ? t('正常') : t('异常') }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="cluster_name"
        ellipsis
        :min-width="140"
        :title="t('集群名称')" />
      <TableColumn
        col-key="db_module_id"
        ellipsis
        :filter="columnFilter['db_module_id']"
        :min-width="100"
        :title="t('所属模块')">
        <template #default="{ row }: { row: ResourceItem }">
          {{ row.db_module_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_cloud_id"
        ellipsis
        :filter="columnFilter['bk_cloud_id']"
        :min-width="120"
        :title="t('管控区域')">
        <template #default="{ row }: { row: ResourceItem }">
          {{ row.bk_cloud_name }}
        </template>
      </TableColumn>
      <AppendColumnList
        :active-tab="activeTab"
        :column-filter="columnFilter" />
    </template>
  </DbTable>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';
  import type { Exposes as DbTableExposes } from '@components/db-table/IndexNew.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import { TableColumn } from '@components/tdesign-ui/table';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterDetailRelatedTicket from '@views/db-manage/common/ClusterDetailRelatedTicket.vue';

  import { transfromDataToQuery } from '@utils';

  import type { TabItem } from '../Index.vue';

  import AppendColumnList from './AppendColumnList.vue';
  import { transBkuiColumns } from './columns';
  import { type ResourceItem, tableConfigMap } from './tableConfig';
  import { useSelectorSearch } from './useSelectorSearch';

  interface Props {
    // tab id，与 tabListMap / tableConfigMap 的 key 一致，取值含 tendbhaSlave 这类非 ClusterTypes 的值
    activeTab: string;
    columnStatusFilter?: TabItem['columnStatusFilter'];
    customColums?: TabItem['customColums'];
    disabledRowConfig: NonNullable<TabItem['disabledRowConfig']>;
    getResourceList: NonNullable<TabItem['getResourceList']>;
    // 多选模式
    multiple: TabItem['multiple'];
    searchSelectList?: TabItem['searchSelectList'];
    selected: ResourceItem[];
  }

  type Emits = (e: 'change', value: ResourceItem[]) => void;

  defineOptions({
    inheritAttrs: false,
  });

  const props = withDefaults(defineProps<Props>(), {
    columnStatusFilter: undefined,
    customColums: undefined,
    searchSelectList: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 每个 tab 一个组件实例（父级按 activeTab 加了 key），配置只在 setup 期取一次即可
  // 兜底空配置：tabListMap 新增了 tab 但漏配 tableConfigMap 时，退化成无搜索条件而不是整个弹窗报错
  const tableConfig = tableConfigMap[props.activeTab] ?? { searchAttrs: [] };

  const tableRef = useTemplateRef<DbTableExposes>('tableRef');

  const { columnAttrs, searchSelectData, searchValue } = useSelectorSearch(
    tableConfig.searchClusterType ?? props.activeTab,
    tableConfig.searchAttrs,
    props.searchSelectList,
  );

  const customColumnList = computed<PrimaryTableCol[] | undefined>(() =>
    props.customColums ? transBkuiColumns(props.customColums) : undefined,
  );

  const statusFilter = computed(() => ({
    list: [
      {
        label: t('正常'),
        value: 'normal',
      },
      {
        label: t('异常'),
        value: 'abnormal',
      },
    ],
    showConfirmAndReset: true,
    type: 'multiple' as const,
  }));

  // 列筛选候选项来自 queryBizClusterAttrs，没拉到候选项的字段取值为 undefined，对应列不挂筛选
  const columnFilter = computed(() =>
    _.mapValues(columnAttrs.value, (list) => ({
      list: list.map((item) => ({
        label: item.text,
        value: item.value,
      })),
      showConfirmAndReset: true,
      type: 'multiple' as const,
    })),
  );

  // 部分集群类型的正常判定不只看 status 字段，由调用方通过 columnStatusFilter 覆盖
  const isNormalStatus = (row: ResourceItem) =>
    props.columnStatusFilter ? props.columnStatusFilter(row) : row.status === 'normal';

  // 已下线集群置灰展示
  const getRowClass = ({ row }: { row: ResourceItem }) => (row.isOffline ? 'is-offline' : '');

  // 禁用行：命中规则时返回提示文案，DbTable 会据此禁用勾选并把文案作为 tooltip
  const disableSelectMethod = (row: ResourceItem) =>
    props.disabledRowConfig.find((item) => item.handler(row))?.tip ?? false;

  // 上一次实际发出去的搜索条件，用于区分「首次回显」与「用户改了条件」
  let lastSearchValue: Record<string, string> | undefined;

  /**
   * 列表数据的唯一请求入口
   *
   * 搜索栏、列筛选都只写 searchValue，由 DbQuickSearch 规整后统一从这里发请求，
   * 避免同一次操作既走 watch 又走回显触发两次请求
   *
   * 不传 bk_biz_id：这批列表接口的业务 id 都在 URL path 上；
   * 且 DbTable 以 paramsMemo 是否有值判断「是否搜索中」，多余的键会让空状态永远显示成搜索无结果
   */
  const handleSearchChange = (value: Record<string, string>) => {
    // 组件挂载时 DbQuickSearch 会回显一次，那不算条件变化，不能清掉调用方传进来的已选
    if (lastSearchValue && !_.isEqual(value, lastSearchValue)) {
      // 条件变了，结果集不再对应原来的选中项
      emits('change', []);
    }
    lastSearchValue = value;
    tableRef.value?.fetchData(transfromDataToQuery(value));
  };

  const handleFilterChange = (filterValue: Record<string, string | string[]>) => {
    // 搜索栏与筛选面板共用 searchValue，多选列重置时表格会回传数组，入口处统一归一成逗号分隔字符串
    searchValue.value = _.mapValues(filterValue, (value) => (Array.isArray(value) ? value.join(',') : value));
  };

  const handleSelection = (_key: string[], list: ResourceItem[]) => {
    emits('change', list);
  };
</script>

<style lang="less" scoped>
  .cluster-selector-search {
    margin-bottom: 16px;
  }

  .cluster-selector-table {
    :deep(.t-table__body) {
      tr {
        cursor: pointer;

        &.is-offline td {
          color: @light-gray;
        }
      }
    }
  }
</style>
