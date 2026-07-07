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
  <div class="cluster-detail-k8s-opration-record">
    <div class="mb-16">
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="id"
      selectable
      @filter-change="handleFilterChange">
      <TableColumn
        col-key="createdAt"
        :filter="columnFilter?.createdAt"
        :title="t('操作时间')"
        :width="200">
        <template #default="{ row }: { row: KubernetesOperationLogModel }">
          {{ row.createdAtDisplay || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :filter="columnFilter?.creator"
        :title="t('操作人')"
        :width="150">
        <template #default="{ row }: { row: KubernetesOperationLogModel }">
          {{ row.createdBy || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="requestType"
        :filter="columnFilter?.requestType"
        :title="t('操作类型')"
        :width="100">
        <template #default="{ row }: { row: KubernetesOperationLogModel }">
          <BkTag theme="info">{{ row.requestTypeAlias }}</BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="ticket_id"
        :title="t('关联单据')"
        :width="150">
        <template #default="{ row }: { row: KubernetesOperationLogModel }">
          <template v-if="row?.ticketId">
            <TicketStatusTag
              :data="{
                status: row.ticket_status as TicketModel['status'],
                statusText: TicketModel.statusTextMap[row.ticket_status as TicketModel['status']],
              }" />
            <RouterLink
              class="ml-4"
              target="_blank"
              :to="{
                name: 'bizTicketManage',
                params: {
                  ticketId: row.ticketId,
                },
              }">
              {{ row.ticket_type_display }}[{{ row.ticketId }}]
            </RouterLink>
          </template>
          <span v-else> -- </span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="clusterName"
        :title="t('操作对象')"
        :width="150">
        <template #default="{ row }: { row: KubernetesOperationLogModel }">
          {{ row.clusterName || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="80">
        <template #default="{ row }">
          <BkButton
            size="small"
            text
            theme="primary"
            @click="() => handleToDetail(row)">
            {{ t('查看明细') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>
    <Detail
      v-if="isShowDetail && currentRowData.id"
      v-model="isShowDetail"
      :data="currentRowData" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import KubernetesOperationLogModel from '@services/model/kubernetes/kubernetes-operation-log';
  import SurrealdbHaModel from '@services/model/surrealdb/surrealdb-ha';
  import TicketModel from '@services/model/ticket/ticket';
  import { getQdrantHaOperationLog } from '@services/source/qdrantHa';
  import { getSurrealdbHaOperationLog } from '@services/source/surrealdbHa';
  import { getSurrealdbSingleOperationLog } from '@services/source/surrealdbSingle';

  import { useUrlSearch } from '@hooks';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { ClusterTypes } from '@/common/const';

  import { URL_K8S_OPERATION_MEMO_KEY } from '../../constants';

  import Detail from './components/Detail.vue';
  import { useColumnFilter } from './useColumnFilter';
  import { useQuickSearch } from './useQuickSearch';

  interface Props {
    clusterData: {
      cluster_name: string;
      components: SurrealdbHaModel['components'];
      k8s_cluster_name: string;
      namespace: string;
    };
    clusterType: ClusterTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const { quickSearchData, quickSearchValue } = useQuickSearch();
  const { data: columnFilter } = useColumnFilter();

  const requestApiMap = {
    [ClusterTypes.K8S_QDRANT_HA]: getQdrantHaOperationLog,
    [ClusterTypes.K8S_SURREALDB_HA]: getSurrealdbHaOperationLog,
    [ClusterTypes.K8S_SURREALDB_SINGLE]: getSurrealdbSingleOperationLog,
  };

  const tableRef = ref();

  const isShowDetail = ref(false);
  const currentRowData = ref({} as KubernetesOperationLogModel);

  const dataSource = (params: ServiceParameters<typeof getSurrealdbHaOperationLog>) =>
    requestApiMap[props.clusterType as keyof typeof requestApiMap]({
      ...params,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      clusterName: props.clusterData.cluster_name,
      k8sClusterName: props.clusterData.k8s_cluster_name,
      namespace: props.clusterData.namespace,
    });

  const fetchData = () => {
    const realQuickSearchValue = Object.keys(quickSearchValue.value)
      .filter((key) => !key.includes('createdAt'))
      .reduce(
        (obj, key) => {
          return Object.assign(obj, { [key]: quickSearchValue.value[key] });
        },
        {} as Record<string, string>,
      );
    const [startTime, endTime] = (quickSearchValue.value?.createdAt || '').split(',');
    const params = {
      ...realQuickSearchValue,
      endTime: endTime || undefined,
      startTime: startTime || undefined,
    };

    tableRef.value.fetchData(params);

    setTimeout(() => {
      router.replace({
        query: {
          ...getSearchParams(),
          [URL_K8S_OPERATION_MEMO_KEY]: encodeURIComponent(JSON.stringify(params)),
        },
      });
    });
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, any>) => {
    quickSearchValue.value = filterValue;
  };

  const handleToDetail = (row: KubernetesOperationLogModel) => {
    currentRowData.value = row;
    isShowDetail.value = true;
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less">
  .cluster-detail-k8s-opration-record {
    height: 100%;
    padding: 18px 0;
  }
</style>
