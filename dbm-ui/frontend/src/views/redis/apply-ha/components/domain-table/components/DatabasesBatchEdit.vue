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
  <BkPopover
    v-model:is-show="showPopover"
    :boundary="body"
    ext-cls="batch-edit"
    theme="light"
    trigger="manual"
    :width="252">
    <BkButton
      class="ml-4"
      text
      theme="primary"
      @click="() => (showPopover = true)">
      <DbIcon
        class="batch-edit-trigger"
        type="bulk-edit" />
    </BkButton>
    <template #content>
      <div class="batch-edit-content">
        <p class="batch-edit-header">
          {{ t('批量编辑 Databases') }}
        </p>
        <div class="batch-edit-box">
          <BkInput
            v-model="databases"
            class="batch-edit-input"
            :max="64"
            :min="2"
            :placeholder="t('范围 2～64')"
            type="number" />
        </div>
        <div class="batch-edit-footer">
          <BkButton
            class="mr-8"
            size="small"
            theme="primary"
            @click="handleConfirm">
            {{ t('确定') }}
          </BkButton>
          <BkButton
            size="small"
            @click="handleCancel">
            {{ t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'change', value: number): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { body } = document;

  const showPopover = ref(false);
  const databases = ref(2);

  watch(showPopover, (show) => {
    if (show === false) {
      databases.value = 2;
    }
  });

  watch(
    () => databases.value,
    (value) => {
      if (value) {
        handleValidate();
      }
    },
  );

  const handleValidate = () => {};

  const handleConfirm = () => {
    handleValidate();

    emits('change', databases.value);
    handleCancel();
  };

  const handleCancel = () => {
    showPopover.value = false;
  };
</script>

<style lang="less" scoped>
  .batch-edit-trigger {
    font-size: 14px;
  }

  .batch-edit {
    .batch-edit-content {
      padding: 6px 2px;
    }

    .batch-edit-header {
      padding-bottom: 4px;
      font-size: @font-size-large;
      color: @title-color;

      span {
        font-size: @font-size-mini;
        color: @default-color;
      }
    }

    .batch-edit-box {
      position: relative;
      color: @default-color;

      .batch-edit-input {
        margin: 20px 0 24px;
      }
    }

    .batch-edit-footer {
      text-align: right;

      .bk-button {
        min-width: 60px;
        font-size: 12px;
      }
    }
  }
</style>
