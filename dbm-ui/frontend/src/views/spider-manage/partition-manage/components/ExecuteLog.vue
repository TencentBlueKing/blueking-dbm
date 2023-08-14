<template>
  <div class="partition-execute-log">
    <BkDatePicker
      v-model="recordTime"
      class="mb-16"
      @change="handleDateChange" />
    <DbTable
      ref="tableRef"
      :columns="tableColumns"
      :data-source="queryLog" />
  </div>
</template>
<script setup lang="ts">
  import {
    nextTick,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PartitionModel from '@services/model/partition/partition';
  import { queryLog } from '@services/partitionManage';

  import { ClusterTypes } from '@common/const';

  interface Props {
    data: PartitionModel
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const recordTime = ref('');

  const tableColumns = [
    {
      label: t('执行时间'),
      field: 'check_info',
    },
    {
      label: t('关联任务'),
      field: 'ticket_id',
    },
    {
      label: t('执行状态'),
      field: 'ticket_status',
    },
    {
      label: t('失败原因'),
      field: 'check_info',
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData({}, {
      cluster_type: ClusterTypes.SPIDER,
      config_id: props.data.id,
      date: recordTime.value,
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
</script>
<style lang="less">
  .partition-execute-log {
    padding: 28px 24px;
  }
</style>
