<template>
  <BkDialog
    class="batch-assign-dialog"
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
        <FormPanel
          ref="formPanelRef"
          :biz-id="curBizId"
          :current-data="currentData" />
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
        <span
          v-bk-tooltips="{
            disabled: !!hostList.length,
            content: t('请选择主机'),
          }">
          <BkButton
            :disabled="!hostList.length"
            :loading="isUpdating"
            theme="primary"
            @click="handleSubmit">
            {{ t('确定') }}
          </BkButton>
        </span>
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

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { updateResource } from '@services/source/dbresourceResource';

  import { messageSuccess } from '@utils';

  import FormPanel from './components/FormPanel.vue';
  import ListPanel from './components/ListPanel.vue';

  interface Props {
    selected: DbResourceModel[];
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const formPanelRef = useTemplateRef('formPanelRef');

  const width = Math.ceil(window.innerWidth * 0.67);
  const contentHeight = Math.ceil(window.innerHeight * 0.67 - 48);
  const layoutStyle = {
    height: `${contentHeight}px`,
  };

  const hostList = shallowRef<DbResourceModel[]>([]);

  const curBizId = computed(() => hostList.value[0]?.for_biz.bk_biz_id || 0);

  const currentData = computed(() => {
    if (props.selected.length === 1) {
      const { for_biz: forBiz, labels, resource_type: resourceType } = props.selected[0];
      return {
        forBiz,
        labels: labels,
        resourceType,
      };
    }
    return undefined;
  });

  const { loading: isUpdating, run: runUpdate } = useRequest(updateResource, {
    manual: true,
    onSuccess() {
      emits('refresh');
      isShow.value = false;
      messageSuccess('设置成功');
    },
  });

  watch(
    () => props.selected,
    () => {
      hostList.value = props.selected;
    },
  );

  const handleUpdate = (data: DbResourceModel[]) => {
    hostList.value = data;
  };

  const handleSubmit = async () => {
    const data = await formPanelRef.value!.getValue();
    runUpdate({
      bk_host_ids: hostList.value.map((item) => item.bk_host_id),
      for_biz: data.for_biz as number,
      labels: data.labels,
      rack_id: '',
      resource_type: data.resource_type as string,
      storage_device: {},
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .batch-assign-dialog {
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
