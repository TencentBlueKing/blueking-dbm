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
    <div class="event-change__operations mb-16">
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
      :columns="columns"
      :data-source="dataSource"
      fixed-pagination
      releate-url-query
      @clear-search="handleClearFilters" />
  </div>
</template>

<script setup lang="tsx">
  import { format, subDays } from 'date-fns';
  import { nextTick } from 'vue';
  import { useI18n } from 'vue-i18n';

  import {
    getClusterOperateRecords,
    getInstanceOperateRecords,
  } from '@services/source/ticket';

  import DbStatus from '@components/db-status/index.vue';

  interface Props {
    id: number, // 集群 or 实例 id
    isFetchInstance?: boolean
  }

  type IRowData = ServiceReturnType<typeof getInstanceOperateRecords>['results'][number]

  const props = withDefaults(defineProps<Props>(), {
    isFetchInstance: false,
  });

  const { t } = useI18n();

  const tableRef = ref();

  const daterange = ref<[string, string]|[Date, Date]>([subDays(new Date(), 6), new Date()])

  const dataSource = computed(() => (props.isFetchInstance ? getInstanceOperateRecords : getClusterOperateRecords));

  const columns = [
    {
      label: t('时间'),
      field: 'create_at',
    }, {
      label: t('操作类型'),
      field: 'op_type',
    }, {
      label: t('操作结果'),
      field: 'op_status',
      render: ({ data }: {data: IRowData}) => {
        const errorStatus = { text: t('失败'), theme: 'danger' };
        const successStatus = { text: t('成功'), theme: 'success' };
        const loadingStatus = { text: t('执行中'), theme: 'loading' };
        const statusInfoMap = {
          PENDING: loadingStatus,
          RUNNING: loadingStatus,
          SUCCEEDED: successStatus,
          FAILED: errorStatus,
          REVOKED: errorStatus,
        };
        const status = statusInfoMap[data.op_status] || errorStatus;
        return <DbStatus type="linear" theme={status.theme}>{status.text}</DbStatus>;
      },
    }, {
      label: t('操作人'),
      field: 'creator',
    }, {
      label: t('单据链接'),
      field: 'ticket_id',
      render: ({ data }: {data: IRowData}) => (
        <router-link
          to={{
            name: 'bizTicketManage',
            query: {
              id: data.ticket_id,
            },
          }}
          target="_blank">
          { data.ticket_id }
        </router-link>
      ),
    },
  ];

  const fetchData = () => {
    nextTick(() => {
      if (!props.id) return;

      const [start, end] = daterange.value;
      const dateParams = start && end ? {
        start_time: format(new Date(Number(start)), 'yyyy-MM-dd HH:mm:ss'),
        end_time: format(new Date(Number(end)), 'yyyy-MM-dd HH:mm:ss'),
      } : {
        start_time: '',
        end_time: '',
      };
      const fetchKey = props.isFetchInstance ? 'instance_id' : 'cluster_id';
      tableRef.value.fetchData({
        ...dateParams,
      }, {
        [fetchKey]: props.id,
      });
    });
  };

  watch(() => props.id, () => {
    fetchData();
  }, {
    immediate: true,
  });

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
