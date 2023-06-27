<template>
  <BkPopover
    :disabled="!taskIdList || taskIdList.length < 1"
    placement="top"
    theme="light">
    <BkBadge
      :count="taskIdList?.length"
      theme="danger"
      :visible="!taskIdList || taskIdList.length < 1">
      <BkButton
        class="w88"
        theme="primary"
        @click="handleExportHost">
        {{ t('导入') }}
      </BkButton>
    </BkBadge>
    <template #content>
      当前已经有
      <span style="padding: 0 2px; font-weight: bold;">{{ taskIdList?.length }}</span>
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

  const {
    data: taskIdList,
  } = useRequest(fetchImportTask, {
    manual: false,
  });

  const handleExportHost = () => {
    emits('exportHost');
  };

  const handleGoDatabaseMission = () => {
    router.push({
      name: 'DatabaseMission',
      query: {
        id: taskIdList.value?.join(','),
      },
    });
  };
</script>
