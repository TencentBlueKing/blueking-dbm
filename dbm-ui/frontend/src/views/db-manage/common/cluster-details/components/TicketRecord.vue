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
  <div class="cluster-detail-event-change">
    <div class="mb-16">
      <BkDatePicker
        v-model="daterange"
        append-to-body
        :placeholder="t('请选择')"
        style="width: 410px"
        type="datetimerange"
        @change="handleDateChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      row-key="ticket_id"
      @clear-search="handleClearFilters">
      <TableColumn
        col-key="ticket_id"
        :min-width="80"
        :title="t('单号')">
        <template #default="{ row }: { row: IRowData }">
          <RouterLink
            target="_blank"
            :to="{
              name: 'bizTicketManage',
              params: {
                ticketId: row.ticket_id,
              },
            }">
            {{ row.ticket_id }}
          </RouterLink>
        </template>
      </TableColumn>
      <TableColumn
        col-key="op_type"
        :min-width="300"
        :title="t('单据类型')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.op_type || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="op_status"
        :min-width="120"
        :title="t('单据状态')">
        <template #default="{ row }: { row: IRowData }">
          <TicketStatusTag
            :data="{
              status: row.op_status as TicketModel['status'],
              statusText: TicketModel.statusTextMap[row.op_status as TicketModel['status']],
            }" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="remark"
        :min-width="150"
        :title="t('备注')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.remark || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :min-width="150"
        :title="t('提单人')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.creator || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="create_at"
        fixed="left"
        :min-width="250"
        :title="t('提单时间')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.create_at || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getClusterOperateRecords } from '@services/source/ticket';

  import { useUrlSearch } from '@hooks';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { URL_RECORD_MEMO_KEY } from '../constants';

  interface Props {
    id: number;
  }

  type IRowData = ServiceReturnType<typeof getClusterOperateRecords>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const urlPaylaod = JSON.parse(decodeURIComponent(String(route.query[URL_RECORD_MEMO_KEY] || '{}')));

  const tableRef = ref();
  const daterange = ref<[string, string] | [Date, Date]>([
    dayjs().subtract(6, 'day').format('YYYY-MM-DD 00:00:00'),
    dayjs().format('YYYY-MM-DD 23:59:59'),
  ]);

  if (_.has(urlPaylaod, 'start_time') && _.has(urlPaylaod, 'end_time')) {
    daterange.value = [urlPaylaod.start_time, urlPaylaod.end_time];
  }

  const dataSource = (params: ServiceParameters<typeof getClusterOperateRecords>) =>
    getClusterOperateRecords({
      ...params,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.id,
    });

  const fetchData = () => {
    const [startTime, endTime] = daterange.value;
    const params = {
      end_time: endTime ? dayjs(endTime).format('YYYY-MM-DD HH:mm:ss') : '',
      start_time: startTime ? dayjs(startTime).format('YYYY-MM-DD HH:mm:ss') : '',
    };

    tableRef.value.fetchData(params);

    setTimeout(() => {
      router.replace({
        query: {
          ...getSearchParams(),
          [URL_RECORD_MEMO_KEY]: encodeURIComponent(JSON.stringify(params)),
        },
      });
    });
  };

  const handleDateChange = () => {
    fetchData();
  };

  const handleClearFilters = () => {
    daterange.value = ['', ''];
    fetchData();
  };

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .cluster-detail-event-change {
    padding: 16px 0;
  }
</style>
