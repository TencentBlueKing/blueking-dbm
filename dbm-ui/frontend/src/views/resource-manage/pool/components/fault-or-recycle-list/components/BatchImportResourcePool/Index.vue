<template>
  <BkDialog
    class="batch-import-dialog"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    render-directive="if"
    :width="width"
    @closed="handleCancel">
    <BkResizeLayout
      :border="false"
      collapsible
      :initial-divide="400"
      placement="right"
      :style="layoutStyle">
      <template #main>
        <FormPanel ref="formPanelRef" />
      </template>
      <template #aside>
        <ListPanel
          ref="formRef"
          v-model="hostList"
          :content-height="contentHeight"
          @update:host-list="handleUpdate" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <div>
        <BkButton
          v-bk-tooltips="tooltip"
          :disabled="!hostList.length"
          :loading="isUpdating"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { importResource } from '@services/source/dbresourceResource';

  import { useSystemEnviron } from '@stores';

  import { useImportResourcePoolTooltip } from '../../../hooks/useImportResourcePoolTip';

  import FormPanel from './components/FormPanel.vue';
  import ListPanel from './components/ListPanel.vue';

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const hostList = defineModel<FaultOrRecycleMachineModel[]>('hostList', {
    default: () => [],
  });

  type Emits = (e: 'refresh') => void;

  const { t } = useI18n();
  const systemEnvironStore = useSystemEnviron();

  const formPanelRef = useTemplateRef('formPanelRef');
  const { successMessage, tooltip } = useImportResourcePoolTooltip(hostList);

  const width = Math.ceil(window.innerWidth * 0.8);
  const contentHeight = Math.ceil(window.innerHeight * 0.8 - 48);
  const layoutStyle = {
    height: `${contentHeight}px`,
  };

  const { loading: isUpdating, run: runImport } = useRequest(importResource, {
    manual: true,
    onSuccess({ task_ids: taskIds }) {
      handleCancel();
      successMessage(taskIds);
    },
  });

  const handleUpdate = (data: FaultOrRecycleMachineModel[]) => {
    hostList.value = data;
  };

  const handleSubmit = async () => {
    const data = await formPanelRef.value!.getValue();
    runImport({
      bk_biz_id: systemEnvironStore.urls.DBA_APP_BK_BIZ_ID,
      for_biz: data.for_biz as number,
      hosts: hostList.value.map((item) => ({
        bk_cloud_id: item.bk_cloud_id,
        host_id: item.bk_host_id,
        ip: item.ip,
      })),
      labels: data.labels,
      resource_type: data.resource_type as string,
      return_resource: true,
    });
  };

  const handleCancel = () => {
    emits('refresh');
    isShow.value = false;
  };
</script>

<style lang="less">
  .batch-import-dialog {
    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }

    .bk-modal-close {
      display: none !important;
    }
  }
</style>
