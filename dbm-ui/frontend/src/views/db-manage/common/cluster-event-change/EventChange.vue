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
  <div class="event-change db-scroll-y">
    <div class="event-change-operations mb-16">
      <BkDatePicker
        v-model="daterange"
        append-to-body
        :placeholder="$t('请选择')"
        style="width: 410px"
        type="datetimerange"
        @change="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      fixed-pagination
      releate-url-query
      row-key="ticket_id"
      @clear-search="handleClearFilters">
      <TableColumn
        col-key="create_at"
        :title="t('时间')" />
      <TableColumn
        col-key="op_type"
        :title="t('操作类型')" />
      <TableColumn
        col-key="op_status"
        :title="t('操作结果')">
        <template #default="{ row }">
          <DbStatus
            :theme="getOpStatusInfo(row.op_status).theme"
            type="linear">
            {{ getOpStatusInfo(row.op_status).text }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :title="t('操作人')" />
      <TableColumn
        col-key="ticket_id"
        :title="t('单据链接')">
        <template #default="{ row }">
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
    </DbTable>
  </div>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { nextTick } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getClusterOperateRecords, getInstanceOperateRecords } from '@services/source/ticket';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  interface Props {
    id: number; // 集群 or 实例 id
    isFetchInstance?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    isFetchInstance: false,
  });

  const { t } = useI18n();

  const tableRef = ref();

  const daterange = ref<[string, string] | [Date, Date]>([dayjs().subtract(6, 'day').toDate(), new Date()]);

  const dataSource = computed(() => (props.isFetchInstance ? getInstanceOperateRecords : getClusterOperateRecords));

  const getOpStatusInfo = (status: string) => {
    const errorStatus = { text: t('失败'), theme: 'danger' };
    const successStatus = { text: t('成功'), theme: 'success' };
    const loadingStatus = { text: t('执行中'), theme: 'loading' };
    const statusInfoMap: Record<string, { text: string; theme: string }> = {
      FAILED: errorStatus,
      PENDING: loadingStatus,
      REVOKED: errorStatus,
      RUNNING: loadingStatus,
      SUCCEEDED: successStatus,
    };
    return statusInfoMap[status] || errorStatus;
  };

  const fetchData = () => {
    nextTick(() => {
      if (!props.id) return;

      const [start, end] = daterange.value;
      const dateParams =
        start && end
          ? {
              end_time: dayjs(Number(end)).format('YYYY-MM-DD HH:mm:ss'),
              start_time: dayjs(Number(start)).format('YYYY-MM-DD HH:mm:ss'),
            }
          : {
              end_time: '',
              start_time: '',
            };
      const fetchKey = props.isFetchInstance ? 'instance_id' : 'cluster_id';
      tableRef.value.fetchData(
        {
          ...dateParams,
        },
        {
          [fetchKey]: props.id,
        },
      );
    });
  };

  watch(
    () => props.id,
    () => {
      fetchData();
    },
    {
      immediate: true,
    },
  );

  function handleClearFilters() {
    daterange.value = ['', ''];
    fetchData();
  }
</script>

<style lang="less" scoped>
  .event-change {
    height: 100%;
    padding: 24px 0;
  }
</style>
