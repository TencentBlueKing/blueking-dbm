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
  <div class="mongo-host-selector-table">
    <DbQuickSearch
      v-model="quickSearchValue"
      class="mt-16 mb-16"
      :data="quickSearchData"
      :placeholder="t('请输入或选择条件搜索')"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="hostTable"
      class="db-host-table"
      :container-height="containerHeight"
      :data-source="realDataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="quickSearchValue"
      row-key="ip"
      :rowspan-and-colspan="rowspanAndColspan"
      :select-single="single"
      selectable
      :selected="selected"
      @filter-change="handleFilterChange"
      @request-success="handleRequestSuccess"
      @selection="handleSelection">
      <TableColumn
        col-key="ip"
        fixed="left"
        :min-width="140"
        :title="t('主机IP')">
      </TableColumn>
      <!-- <TableColumn
        col-key="instance_address"
        :min-width="160"
        :title="t('实例')">
      </TableColumn> -->
      <TableColumn
        col-key="role"
        :min-width="160"
        :title="t('角色')">
        <template #default="{ row }: { row: IRowData }">
          {{ renderRole(row) }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.alive"
        :title="t('Agent状态')"
        width="96">
        <template #default="{ row }: { row: IRowData }">
          <DbStatus :theme="row.host_info?.alive === 1 ? 'success' : 'danger'">
            {{ row.host_info?.alive === 1 ? t('正常') : t('异常') }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.alive"
        :title="t('Agent状态')"
        width="96">
        <template #default="{ row }: { row: IRowData }">
          <DbStatus :theme="row.host_info?.alive === 1 ? 'success' : 'danger'">
            {{ row.host_info?.alive === 1 ? t('正常') : t('异常') }}
          </DbStatus>
        </template>
      </TableColumn>
      <!-- <TableColumn
        col-key="status"
        :min-width="120"
        :title="t('实例状态')">
        <template #default="{ row }: { row: IRowData }">
          <DbStatus :theme="getStatusInfo(row).theme">{{ getStatusInfo(row).text }}</DbStatus>
        </template> -->
      <!-- </TableColumn> -->
      <TableColumn
        col-key="related_clusters"
        :min-width="200"
        :title="t('关联集群')">
        <template #default="{ row }: { row: IRowData }">
          <div
            v-if="row.related_clusters?.length"
            class="mongo-host-related-list">
            <div
              v-for="item in row.related_clusters"
              :key="item.immute_domain"
              v-overflow-tips
              class="text-overflow">
              {{ item.immute_domain }}
            </div>
          </div>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_cloud_id"
        :title="t('管控区域')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_cloud_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_sub_zone"
        :title="t('园区')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_sub_zone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_rack_id"
        :title="t('机架ID')"
        :width="100">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_rack_id || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.host_name"
        :title="t('主机名称')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          {{ row.host_info?.host_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.os_name"
        :title="t('操作系统')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          {{ row.host_info?.os_name || '--' }}
        </template>
      </TableColumn>

      <TableColumn
        col-key="bk_svr_device_cls_name"
        :title="t('机型')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_svr_device_cls_name || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import type { PrimaryTableProps } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { queryBizClusterAttrs } from '@services/source/dbbase';
  import { getMongoInstancesList } from '@services/source/mongodb';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex, ipv4 } from '@common/regex';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { type DisableSelectMethod, type MongoHostFetchParams, type MongoHostRow } from '../types';

  export interface Props {
    containerHeight?: number;
    disableSelectMethod?: DisableSelectMethod;
    fetchParams?: MongoHostFetchParams;
    selected: MongoHostRow[];
    single?: boolean;
  }

  type Emits = (e: 'selection', list: IRowData[]) => void;

  type IRowData = MongoHostRow;

  const props = withDefaults(defineProps<Props>(), {
    containerHeight: 570 - 32 - 16, // 去除搜索框高度和 margin
    disableSelectMethod: undefined,
    fetchParams: undefined,
    single: false,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const hostTableRef = useTemplateRef('hostTable');

  // 搜索候选项 cluster_type：优先 fetchParams，缺省覆盖两类 Mongo 集群（对齐 host-selector）
  const searchClusterType = computed(
    () =>
      props.fetchParams?.cluster_type || [ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGO_REPLICA_SET].join(','),
  );

  // instancelist 数据源：fetchParams 固定过滤 + 分页/搜索参数
  const realDataSource = (params: ServiceParameters<typeof getMongoInstancesList>) =>
    getMongoInstancesList({
      ...props.fetchParams,
      ...params,
      extra: 1,
    });

  const quickSearchData = [
    {
      id: 'ip',
      name: 'IP',
      type: 'multiple-input' as const,
      validator: (value: string) => {
        if (value.split(batchSplitRegex).some((item) => !ipv4.test(item))) {
          return t('格式错误');
        }
        return true;
      },
    },
    {
      id: 'bk_cloud_id',
      name: t('管控区域'),
      remoteMethod: () =>
        queryBizClusterAttrs({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_attrs: 'bk_cloud_id',
          cluster_type: searchClusterType.value as ClusterTypes,
        }).then((data) => (data.bk_cloud_id || []).map((item) => ({ label: item.text, value: item.value }))),
      type: 'multiple' as const,
    },
  ];

  const quickSearchValue = ref<Record<string, any>>({});

  // 供 rowspan 合并使用：记录当前页数据
  const pageRows = shallowRef<IRowData[]>([]);

  const fetchData = () => {
    hostTableRef.value?.fetchData(Object.assign({}, quickSearchValue.value));
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const handleRequestSuccess = (data: { results: IRowData[] }) => {
    pageRows.value = data.results;
  };

  const handleSelection = (_key: string[], list: IRowData[]) => {
    emits('selection', list);
  };

  // 角色列合并：同集群(master_domain) + 同角色(machine_type) 合并，mongodb 分片实例再按 shard 细分
  const rowspanAndColspan: PrimaryTableProps['rowspanAndColspan'] = ({ col, row, rowIndex }) => {
    if (col.colKey !== 'role') {
      return {};
    }
    const rows = pageRows.value;
    if (rows.length === 0) {
      return {};
    }
    const isSameGroup = (item: IRowData) =>
      item.machine_type === 'mongodb'
        ? item.master_domain === row.master_domain && item.machine_type === row.machine_type && item.shard === row.shard
        : item.master_domain === row.master_domain && item.machine_type === row.machine_type;
    const firstRowIndex = rows.findIndex(isSameGroup);
    if (firstRowIndex !== rowIndex) {
      return {};
    }
    return { rowspan: rows.filter(isSameGroup).length };
  };

  const renderRole = (row: IRowData) => {
    if (row.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && row.machine_type === 'mongodb' && row.shard) {
      return row.shard;
    }
    return row.machine_type || '--';
  };

  // const getStatusInfo = (row: IRowData) => {
  //   if (row.isRebooting) {
  //     return { text: t('重建中'), theme: 'warning' };
  //   }
  //   if (row.status === 'running') {
  //     return { text: t('正常'), theme: 'success' };
  //   }
  //   return { text: t('异常'), theme: 'danger' };
  // };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less">
  .mongo-host-selector-table {
    height: 570px;
    padding: 0 24px;

    .mongo-host-related-list {
      padding: 6px 0;

      > div {
        line-height: 18px;
      }
    }
  }
</style>
