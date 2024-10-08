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

  import { messageSuccess } from '@utils';

  import FormPanel from './components/FormPanel.vue';
  import ListPanel from './components/ListPanel.vue';

  interface Emits {
    (e: 'refresh'): void;
  }

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  const hostList = defineModel<FaultOrRecycleMachineModel[]>('hostList', {
    default: () => [],
  });

  const { t } = useI18n();
  const formPanelRef = useTemplateRef('formPanelRef');
  const router = useRouter();



  const tooltip = computed(() => {
    const path = router.resolve({
      name: 'taskHistory'
    });
    return !hostList.value.length
      ? {
        disabled: !!hostList.value.length,
        content: t('请选择主机'),
      }
      : {
        theme: 'light',
        content: () => (
          <div>
            {t('提交后，将会进行主机初始化任务，具体的导入结果，可以通过“')}
            <a href={path.href} target='_blank'>
              {t('任务历史')}
            </a>
            {t('”查看')}
          </div>
        )
      }
  });

  const width = Math.ceil(window.innerWidth * 0.8);
  const contentHeight = Math.ceil(window.innerHeight * 0.8 - 48);
  const layoutStyle = {
    height: `${contentHeight}px`,
  };

  const { loading: isUpdating, run: runImport } = useRequest(importResource, {
    manual: true,
    onSuccess() {
      handleCancel();
      messageSuccess(t('操作成功'));
    },
  });

  const handleUpdate = (data: FaultOrRecycleMachineModel[]) => {
    hostList.value = data;
  };

  const handleSubmit = async () => {
    const data = await formPanelRef.value!.getValue();
    runImport({
      hosts: hostList.value.map((item) => ({
        ip: item.ip,
        host_id: item.bk_host_id,
        bk_cloud_id: item.bk_cloud_id,
      })),
      for_biz: data.for_biz as number,
      resource_type: data.resource_type as string,
      labels: data.labels,
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
