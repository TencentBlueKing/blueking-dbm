<template>
  <div class="partition-execute-log">
    <BkDatePicker
      v-model="recordTime"
      class="mb-16"
      type="daterange"
      @change="handleDateChange" />
    <DbTable
      ref="tableRef"
      :columns="tableColumns"
      :data-source="queryLog"
      @clear-search="handleClearSearch" />
  </div>
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import {
    nextTick,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PartitionModel from '@services/model/partition/partition';
  import type PartitionLogModel from '@services/model/partition/partition-log';
  import { queryLog } from '@services/partitionManage';

  import { ClusterTypes } from '@common/const';

  interface Props {
    data: PartitionModel
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const recordTime = ref<[string, string]>([
    dayjs().date(-100)
      .format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);

  const tableColumns = [
    {
      label: t('执行时间'),
      field: 'execute_time',
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      render: ({ data }: {data: PartitionLogModel}) => (data.ticket_id ? (
        <router-link
          target="_blank"
          to={{
            name: 'SelfServiceMyTickets',
            query: {
              filterId: data.ticket_id,
            },
          }}>
          {data.ticket_id}
        </router-link>
        ) : '--'),
    },
    {
      label: t('执行状态'),
      field: 'status',
      render: ({ data }: {data: PartitionLogModel}) => (
        <div>
          <db-icon
            class={{ 'rotate-loading': data.isRunning }}
            style="vertical-align: middle;"
            type={data.statusIcon}
            svg />
          <span
            v-bk-tooltips={{
              disabled: !data.isFailed && data.check_info,
              content: data.check_info,
              extCls: 'partition-execute-error-message-pop',
            }}
            class="ml-4">
            {data.statusText}
          </span>
        </div>
      ),
    },
    {
      label: t('失败原因'),
      field: 'check_info',
      render: ({ data }: {data: PartitionLogModel}) => data.check_info || '--',
    },
  ];

  const fetchData = () => {
    const [startTime, endTime] = recordTime.value;
    const params = {};
    if (startTime && endTime) {
      Object.assign(params, {
        start_time: dayjs(startTime).format('YYYY-MM-DD HH:mm:ss'),
        end_time: dayjs(endTime).format('YYYY-MM-DD HH:mm:ss'),
      });
    }
    tableRef.value.fetchData(params, {
      cluster_type: ClusterTypes.SPIDER,
      config_id: props.data.id,
    });
  };

  const handleDateChange = () => {
    fetchData();
  };

  watch(() => props.data, () => {
    nextTick(() => {
      fetchData();
    });
  }, {
    immediate: true,
  });

  const handleClearSearch = () => {
    recordTime.value = [
      dayjs().date(-100)
        .format('YYYY-MM-DD HH:mm:ss'),
      dayjs().format('YYYY-MM-DD HH:mm:ss'),
    ];
    fetchData();
  };
</script>
<style lang="less">
  .partition-execute-log {
    padding: 28px 24px;
  }

  .partition-execute-error-message-pop{
    max-width: 350px;;
  }
</style>
