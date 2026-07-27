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
  <DbDialog
    v-model:is-show="modelValue"
    class="import-host-dialog"
    :confirm-button-disable-info="{
      disabled: hostSelectList.length === 0,
      tooltips: submitButtonTooltips,
    }"
    :confirm-handler="handleSubmit"
    :esc-close="false"
    :quick-close="false"
    render-directive="if"
    :width="width"
    @hidden="handleHidden">
    <BkResizeLayout
      :border="false"
      collapsible
      :initial-divide="400"
      placement="right"
      :style="layoutStyle">
      <template #main>
        <SelectHostPanel
          v-if="modelValue"
          ref="selectHostPanelRef"
          v-model="hostSelectList"
          :content-height="contentHeight" />
      </template>
      <template #aside>
        <FormPanel
          ref="formRef"
          v-model:host-list="hostSelectList"
          :error-host-map="errorHostMap" />
      </template>
    </BkResizeLayout>
    <ImportResourceErrorMessage
      v-model="isErrorMessageShow"
      :ips="errorHostList"
      :message-list="errorMessageList" />
  </DbDialog>
</template>
<script setup lang="tsx">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { importResource } from '@services/source/dbresourceResource';
  import type { HostInfo } from '@services/types';

  import { useTicketMessage } from '@hooks';

  import ImportResourceErrorMessage from '@views/resource-manage/common/components/import-resource-error-message/Index.vue';
  import { useImportResourceErrorMessage } from '@views/resource-manage/common/hooks/useImportResourceErrorMessage.ts';

  import FormPanel from './components/FormPanel.vue';
  import SelectHostPanel from './components/select-host-panel/Index.vue';

  interface Props {
    type?: 'business' | 'global';
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    type: 'global',
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const {
    errorHostList,
    errorHostMap,
    errorMessageList,
    handleChange: handleErrorChange,
    handleReset: handleErrorReset,
  } = useImportResourceErrorMessage();

  const formRef = useTemplateRef('formRef');
  const selectHostPanelRef = useTemplateRef('selectHostPanelRef');

  const hostSelectList = shallowRef<HostInfo[]>([]);
  const isErrorMessageShow = ref(false);

  const submitButtonTooltips = computed(() => {
    if (hostSelectList.value.length === 0) {
      return {
        content: t('请选择主机'),
        disabled: false,
      };
    }
    if (hostSelectList.value.some((hostItem) => errorHostMap.value[hostItem.ip])) {
      return {
        content: t('请先处理有问题的 IP'),
        disabled: false,
      };
    }
    return {
      content: '',
      disabled: true,
    };
  });

  const ticketMessage = useTicketMessage({
    isCurrentBiz: props.type === 'business',
  });

  const width = Math.ceil(window.innerWidth * 0.8);
  const contentHeight = Math.ceil(window.innerHeight * 0.8 - 48);
  const layoutStyle = {
    height: `${contentHeight}px`,
  };

  const handleSubmit = () =>
    Promise.all([selectHostPanelRef.value!.getValue(), formRef.value!.getValue()]).then(
      ([selectHostPanelData, fromData]) =>
        importResource({
          ...selectHostPanelData,
          ...fromData,
          hosts: hostSelectList.value.map((item) => ({
            bk_cloud_id: item.cloud_id,
            host_id: item.host_id,
            ip: item.ip,
          })),
        })
          .then(({ ticket_ids: ticketIds }) => {
            window.changeConfirm = false;
            ticketMessage(ticketIds);
            handleCancel();
            emits('change');
          })
          .catch((error) => {
            handleErrorChange(error);
            isErrorMessageShow.value = true;
          }),
    );

  const handleCancel = () => {
    modelValue.value = false;
  };

  const handleHidden = () => {
    handleErrorReset();
    isErrorMessageShow.value = false;
  };
</script>
<style lang="less">
  .import-host-dialog {
    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }
  }
</style>
