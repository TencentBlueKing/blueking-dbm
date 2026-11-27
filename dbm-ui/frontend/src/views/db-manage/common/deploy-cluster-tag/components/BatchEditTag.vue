<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <span
    ref="rootRef"
    v-bind="$attrs"
    class="batch-edit-tag-trigger"
    @click.stop=""
    @mouseleave="handleTriggerMouseLeave">
    <BkButton
      v-bk-tooltips="{
        content: t('统一设置：将该列统一设置为相同的值'),
        disabled: isTooltipDisabled,
      }"
      text
      theme="primary"
      @click="handleShow">
      <DbIcon type="bulk-edit" />
    </BkButton>
  </span>
  <div style="display: none">
    <div
      ref="popRef"
      class="batch-edit-column-select-new">
      <div class="main-title">{{ t('统一设置') }}{{ t('集群标签') }}</div>
      <TagOperation
        ref="tagOperationRef"
        :biz-id="bizId" />
      <div class="footer-box">
        <BkButton
          :loading="confirmLoading"
          size="small"
          style="margin-left: auto"
          theme="primary"
          @click="handleConfirm">
          {{ t('确认') }}
        </BkButton>
        <BkButton
          class="ml-8"
          size="small"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import TagOperation from '@views/db-manage/common/cluster-batch-add-tag/components/tag-operation/Index.vue';

  interface Props {
    /** 标签候选查询的业务 ID */
    bizId?: number | '';
  }

  type Emits = (e: 'change', value: Record<string, string>[]) => void;

  withDefaults(defineProps<Props>(), {
    bizId: window.PROJECT_CONFIG.BIZ_ID,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rootRef = useTemplateRef('rootRef');
  const popRef = useTemplateRef('popRef');
  const tagOperationRef = ref<InstanceType<typeof TagOperation>>();
  const confirmLoading = ref(false);
  const isTooltipDisabled = ref(false);

  let tippyInstance: Instance | undefined;

  const destroyTippy = () => {
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.unmount();
      tippyInstance.destroy();
      tippyInstance = undefined;
    }
  };

  const handleShow = () => {
    isTooltipDisabled.value = true;
    destroyTippy();
    const tippyTarget = rootRef.value;
    if (tippyTarget) {
      tippyInstance = tippy(tippyTarget as SingleTarget, {
        appendTo: () => document.body,
        arrow: true,
        content: popRef.value!,
        hideOnClick: false,
        interactive: true,
        maxWidth: 'none',
        offset: [0, 12],
        placement: 'top-start',
        popperOptions: {
          modifiers: [
            {
              name: 'flip',
              options: {
                allowedAutoPlacements: ['top-start', 'top-end'],
                fallbackPlacements: ['top', 'bottom'],
              },
            },
          ],
          strategy: 'fixed',
        },
        theme: 'light batch-edit-column-theme',
        trigger: 'manual',
        zIndex: 999,
      });
      tippyInstance.show();
    }
  };

  const handleConfirm = async () => {
    try {
      confirmLoading.value = true;
      const tags = await tagOperationRef.value?.getValue(false);
      if (tags === null || tags === undefined || tags.some(({ key, value }) => !key || !value)) {
        return;
      }
      emits(
        'change',
        tags.map(({ key, value }) => ({ [key]: value })),
      );
      tippyInstance!.hide();
    } finally {
      confirmLoading.value = false;
    }
  };

  const handleCancel = () => {
    tippyInstance!.hide();
  };

  const handleTriggerMouseLeave = () => {
    if (!tippyInstance?.state.isVisible) {
      isTooltipDisabled.value = false;
    }
  };

  onBeforeUnmount(() => {
    destroyTippy();
  });
</script>
<style lang="less">
  .batch-edit-tag-trigger {
    display: inline-flex;
    align-items: center;
    vertical-align: middle;
  }

  .batch-edit-column-select-new {
    width: 790px;

    .main-title {
      margin-bottom: 20px;
      font-size: 16px;
      color: #313238;
    }

    .footer-box {
      margin-top: 30px;
      text-align: end;

      button {
        width: 60px;
      }
    }
  }

  .tippy-box[data-theme~='batch-edit-column-theme'] {
    padding: 16px;
    background-color: #fff;
    border: 1px solid #dcdee5 !important;
    border-radius: 4px !important;
    box-shadow: 0 2px 6px 0 rgb(0 0 0 / 10%) !important;

    .tippy-content {
      padding: 0;
      background-color: #fff;
    }
  }
</style>
