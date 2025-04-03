<template>
  <BkPopover
    :disabled="taskNumber < 1"
    placement="top"
    theme="light">
    <BkBadge
      :count="taskNumber"
      theme="danger"
      :visible="taskNumber < 1">
      <AuthButton
        action-id="resource_pool_manage"
        class="w-88"
        theme="primary"
        @click="handleExportHost">
        <DbIcon
          class="mr-6"
          type="add" />
        {{ t('导入主机') }}
      </AuthButton>
    </BkBadge>
    <template #content>
      <I18nT keypath="当前已经有n个导入任务正在进行中，">
        <span class="number">{{ taskNumber }}</span>
      </I18nT>
      <BkButton
        text
        theme="primary"
        @click="handleGoDatabaseMission">
        {{ t('立即查看') }}
      </BkButton>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchImportTask } from '@services/source/dbresourceResource';

  import { useImportResourcePoolTooltip } from '../../hooks/useImportResourcePoolTip';

  type Emits = (e: 'exportHost') => void;

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { getImportTaskHref } = useImportResourcePoolTooltip();

  const taskNumber = computed(() => (taskInfo.value ? taskInfo.value.task_ids.length : 0));

  const { data: taskInfo } = useRequest(fetchImportTask, {
    initialData: {
      bk_biz_id: 0,
      task_ids: [],
    },
    manual: false,
  });

  const handleExportHost = () => {
    emits('exportHost');
  };

  const handleGoDatabaseMission = () => {
    const taskHref = getImportTaskHref(taskInfo.value?.task_ids || []);
    window.open(taskHref, '_blank');
  };
</script>
