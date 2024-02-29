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
  <div class="riak-event-change db-scroll-y">
    <div class="mb-16">
      <BkDatePicker
        v-model="dateRange"
        append-to-body
        :placeholder="t('请选择')"
        style="width: 410px"
        type="datetimerange"
        @change="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      class="riak-event-change-table"
      :columns="columns"
      :data-source="getClusterOperateRecords"
      fixed-pagination
      releate-url-query
      @clear-search="handleClearFilters"
      @request-success="handleRequestSuccess" />
  </div>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { nextTick } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getClusterOperateRecords } from '@services/source/ticket';
  import type { ClusterOperateRecord } from '@services/types/ticket';

  import DbStatus from '@components/db-status/index.vue';

  interface Props {
    id: number,
  }

  const props = defineProps<Props>();
  const loadingCount = defineModel<number>('loadingCount', {
    required: true,
  });

  const router = useRouter();
  const { t } = useI18n();

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

  const columns = [
    {
      label: t('时间'),
      field: 'create_at',
    },
    {
      label: t('操作类型'),
      field: 'op_type',
    },
    // {
    //   label: t('操作对象'),
    //   field: 'op_type',
    //   showOverflowTooltip: false,
    //   render: ({ data }: { data: ClusterOperateRecord }) => (
    //     <>
    //       <RenderRow data={data.ips} />
    //       <bk-button
    //         text
    //         theme="primary"
    //         onclick={ () => handleCopy(data.ips) }>
    //         <db-icon type="copy" />
    //       </bk-button>
    //     </>
    //   ),
    // },
    {
      label: t('操作结果'),
      field: 'op_status',
      render: ({ data }: { data: ClusterOperateRecord }) => {
        const status = statusInfoMap[data.op_status] || errorStatus;
        return (
          <DbStatus
            type="linear"
            theme={status.theme}>
            {status.text}
          </DbStatus>
        );
      },
    },
    {
      label: t('操作人'),
      field: 'creator',
    },
    {
      label: t('单据链接'),
      field: 'ticket_id',
      render: ({ cell }: { cell: number }) => (
        <bk-button
          theme="primary"
          text
          onClick={ () => handleToTicket(cell)}>
          {cell}
        </bk-button>
      ),
    },
  ];

  const tableRef = ref();
  const dateRange = ref([
    dayjs().subtract(6, 'day')
      .format(),
    dayjs().format(),
  ] as [string, string]);

  const fetchData = () => {
    nextTick(() => {
      if (!props.id) return;

      const [start, end] = dateRange.value;
      const dateParams = start && end ? {
        start_time: dayjs(start).format('YYYY-MM-DD HH:mm:ss'),
        end_time: dayjs(end).format('YYYY-MM-DD HH:mm:ss'),
      } : {
        start_time: '',
        end_time: '',
      };

      tableRef.value.fetchData({
        ...dateParams,
      }, {
        cluster_id: props.id,
      });
    });
  };

  watch(() => props.id, () => {
    fetchData();
  }, {
    immediate: true,
  });

  const handleRequestSuccess = ({ results } : { results: ClusterOperateRecord[] }) => {
    loadingCount.value = results.filter(resultItem => ['PENDING', 'RUNNING'].includes(resultItem.op_status)).length;
  };

  const handleClearFilters = () => {
    dateRange.value = ['', ''];
    fetchData();
  };

  const handleToTicket = (id: number) => {
    const localtion = router.resolve({
      name: 'SelfServiceMyTickets',
      query: { id },
    });
    window.open(localtion.href, '_blank');
  };
</script>

<style lang="less" scoped>
  .riak-event-change {
    height: 100%;
    padding: 24px 0;

    :deep(.riak-event-change-table) {
      .bk-table-body {
        max-height: unset !important;
      }
    }
  }
</style>
