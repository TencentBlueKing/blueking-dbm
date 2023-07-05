<template>
  <BkPopover
    :disabled="taskNumber < 1"
    placement="top"
    theme="light">
    <BkBadge
      :count="taskNumber"
      theme="danger"
      :visible="taskNumber < 1">
      <BkButton
        class="w88"
        theme="primary"
        @click="handleExportHost">
        {{ t('导入') }}
      </BkButton>
    </BkBadge>
    <template #content>
      当前已经有
      <span style="padding: 0 2px; font-weight: bold;">{{ taskNumber }}</span>
      个导入任务正在进行中，
      <BkButton
        text
        theme="primary"
        @click="handleGoDatabaseMission">
        立即查看
      </BkButton>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import {
    fetchImportTask,
  } from '@services/dbResource';

  interface Emits{
    (e: 'exportHost'): void
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();

  const taskNumber = computed(() => (taskInfo.value ? taskInfo.value.task_ids.length : 0));

  const {
    data: taskInfo,
  } = useRequest(fetchImportTask, {
    manual: false,
    initialData: {
      bk_biz_id: 0,
      task_ids: [],
    },
  });

  const handleExportHost = () => {
    emits('exportHost');
  };

  const handleGoDatabaseMission = () => {
    router.push({
      name: 'DatabaseMission',
      params: {
        bizId: taskInfo.value?.bk_biz_id,
        id: taskInfo.value?.task_ids.join(','),
      },
    });
  };
</script>
