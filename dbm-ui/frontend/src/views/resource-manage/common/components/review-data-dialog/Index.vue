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
  <BkDialog
    class="review-data-dialog"
    :is-show="isShow"
    :title="title"
    @closed="handleClose">
    <div class="review-data-wrapper">
      <div class="dialog-tip">{{ tip }}</div>
      <BkAlert
        v-if="alert"
        class="mb-8"
        closable
        theme="warning"
        :title="alert" />
      <div class="selected-wrapper">
        <div class="selected-title">
          <I18nT keypath="已选择以下n台主机">
            <span class="selected-count">
              {{ selected.length }}
            </span>
          </I18nT>
        </div>
        <div class="selected-content">
          <div
            v-for="item in selected"
            :key="item"
            class="selected-item">
            {{ item }}
          </div>
        </div>
      </div>
      <BkForm
        v-if="showRemark"
        ref="formRef"
        class="mt-16"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('备注')"
          property="remark"
          required>
          <BkInput
            v-model="formData.remark"
            class="mt-6" />
        </BkFormItem>
      </BkForm>
      <slot name="append" />
    </div>
    <template #footer>
      <div class="dialog-footer">
        <BkButton
          :loading="isLoading"
          style="width: 88px"
          :theme="theme"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-9 operation-btn"
          :disabled="isLoading"
          style="width: 88px"
          @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import type { UnwrapRef, VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { messageSuccess } from '@utils';

  interface Props {
    alert?: string;
    cancelHandler?: () => Promise<any> | void;
    confirmHandler: (value: UnwrapRef<typeof formData>) => Promise<any> | void;
    selected: string[];
    showRemark?: boolean;
    theme?: 'primary' | 'danger';
    tip: string;
    title: string;
  }

  type Emits = (e: 'success', data: Record<string, any>) => void;

  const props = withDefaults(defineProps<Props>(), {
    alert: undefined,
    cancelHandler: () => Promise.resolve(),
    theme: 'primary',
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    append?: () => VNode;
  }>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const formRef = useTemplateRef('formRef');

  const isLoading = ref(false);

  const formData = reactive({
    remark: '',
  });

  const handleConfirm = () => {
    isLoading.value = true;
    Promise.resolve()
      .then(() => formRef.value?.validate())
      .then(() => props.confirmHandler(formData))
      .then((data) => {
        messageSuccess(t('操作成功'));
        emits('success', data);
        isShow.value = false;
        formData.remark = '';
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const handleClose = () => {
    Promise.resolve()
      .then(() => props.cancelHandler())
      .then(() => {
        isShow.value = false;
      });
  };
</script>

<style lang="less" scoped>
  .review-data-wrapper {
    font-size: 14px;

    .dialog-tip {
      padding: 12px 16px;
      margin-bottom: 8px;
      background: #f5f6fa;
      border-radius: 2px;
    }

    .selected-wrapper {
      max-height: 192px;
      overflow-y: auto;
      border: 1px solid #eaebf0;
      border-radius: 2px;

      .selected-title {
        position: sticky;
        top: 0;
        width: 100%;
        padding: 5px 16px;
        color: #313238;
        background: #f0f1f5;

        .selected-count {
          font-weight: 700;
        }
      }

      .selected-content {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        font-size: 12px;

        .selected-item {
          padding: 6px 16px;

          &:nth-child(4n-3),
          &:nth-child(4n-2) {
            background-color: #fff;
          }

          &:nth-child(4n-1),
          &:nth-child(4n) {
            background-color: #fafbfd;
          }
        }
      }
    }

    .remark-label {
      font-size: 12px;
      color: #63656e;
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: center;
  }
</style>

<style lang="less">
  .review-data-dialog {
    .bk-dialog-footer {
      padding-top: 0 !important;
      padding-bottom: 24px !important;
      background-color: #fff !important;
      border: none !important;
    }
  }
</style>
