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
  import { nextTick, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PartitionModel from '@services/model/partition/partition';
  import type PartitionLogModel from '@services/model/partition/partition-log';
  import { queryLog } from '@services/source/partitionManage';

  import { ClusterTypes } from '@common/const';

  interface Props {
    data: PartitionModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const recordTime = ref<[string, string]>([
    dayjs().date(-100).format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);

  const tableColumns = [
    {
      field: 'execute_time',
      label: t('执行时间'),
    },
    {
      field: 'ticket_id',
      label: t('关联单据'),
      render: ({ data }: { data: PartitionLogModel }) =>
        data.ticket_id ? (
          <router-link
            to={{
              name: 'bizTicketManage',
              params: {
                ticketId: data.ticket_id,
              },
            }}
            target='_blank'>
            {data.ticket_id}
          </router-link>
        ) : (
          '--'
        ),
    },
    {
      field: 'status',
      label: t('执行状态'),
      render: ({ data }: { data: PartitionLogModel }) => (
        <div>
          <db-icon
            class={{ 'rotate-loading': data.isRunning }}
            style='vertical-align: middle;'
            type={data.statusIcon}
            svg
          />
          <span
            v-bk-tooltips={{
              content: data.check_info,
              disabled: !data.isFailed && data.check_info,
              extCls: 'partition-execute-error-message-pop',
            }}
            class='ml-4'>
            {data.statusText}
          </span>
        </div>
      ),
    },
    {
      field: 'check_info',
      label: t('失败原因'),
      render: ({ data }: { data: PartitionLogModel }) => data.check_info || '--',
      showOverflowTooltip: {
        popoverOption: {
          maxWidth: 300,
        },
      },
    },
  ];

  const fetchData = () => {
    const [startTime, endTime] = recordTime.value;
    const params = {};
    if (startTime && endTime) {
      Object.assign(params, {
        end_time: dayjs(endTime).format('YYYY-MM-DD HH:mm:ss'),
        start_time: dayjs(startTime).format('YYYY-MM-DD HH:mm:ss'),
      });
    }
    tableRef.value.fetchData(params, {
      cluster_type: ClusterTypes.TENDBHA,
      config_id: props.data.id,
    });
  };

  const handleDateChange = () => {
    fetchData();
  };

  watch(
    () => props.data,
    () => {
      nextTick(() => {
        fetchData();
      });
    },
    {
      immediate: true,
    },
  );

  const handleClearSearch = () => {
    recordTime.value = [dayjs().date(-100).format('YYYY-MM-DD HH:mm:ss'), dayjs().format('YYYY-MM-DD HH:mm:ss')];
    fetchData();
  };
</script>
<style lang="less">
  .partition-execute-log {
    padding: 28px 24px;
  }

  .partition-execute-error-message-pop {
    max-width: 350px;
  }
</style>
