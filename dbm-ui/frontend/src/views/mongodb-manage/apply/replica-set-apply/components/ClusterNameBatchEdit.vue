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
    v-model:is-show="popoverShow"
    :boundary="body"
    ext-cls="batch-edit"
    theme="light"
    trigger="manual"
    :width="540">
    <DbIcon
      type="bulk-edit batch-edit-trigger"
      @click="() => popoverShow = true" />
    <template #content>
      <div class="batch-edit-content">
        <p class="batch-edit-header">
          {{ t('批量录入集群名称') }}
          <span>({{ t('通过换行分隔_快速批量编辑多个名称') }})</span>
        </p>
        <div class="batch-edit-box">
          <BkInput
            v-model="value"
            class="batch-edit-input"
            :placeholder="t('请输入多个集群名称，多个换行分隔')"
            :rows="textareaRows"
            type="textarea" />
          <p
            v-if="errorShow"
            class="batch-edit-error">
            {{ errorText }}
          </p>
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'change', value: string[]): void
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const errorTextMap = {
    repeat: t('输入域名重复'),
    maxlength: t('最大长度为m', { m: 63 }),
  };

  const { body } = document;

  const popoverShow = ref(false);
  const value = ref('');
  const errorShow = ref(false);
  const errorText = ref('');

  const textareaRows = computed(() => {
    const rows = value.value.split('\n').length;
    if (rows <= 5) {
      return 5;
    }
    return rows > 10 ? 10 : rows;
  });

  watch(popoverShow, (show) => {
    if (show === false) {
      value.value = '';
      errorShow.value = false;
    }
  });

  watch(() => value.value, (value) => {
    value && handleValidate();
  });

  const handleValidate = () => {
    const newClusterNames = value.value.split('\n');
    // 最大长度
    const maxlengthRes = newClusterNames.every(key => key.length <= 63);
    if (maxlengthRes === false) {
      errorText.value = errorTextMap.maxlength;
      errorShow.value = true;
      return false;
    }
    // 校验名称是否重复
    const uniqClusterNames = _.uniq(newClusterNames);
    const hasRepeat = newClusterNames.length !== uniqClusterNames.length;
    errorText.value = errorTextMap.repeat;
    errorShow.value = hasRepeat;
    return !hasRepeat;
  };

  const handleConfirm = () => {
    handleValidate();
    if (errorShow.value === true) {
      return;
    }

    emits('change', value.value.split('\n'));
    handleCancel();
  };

  const handleCancel = () => {
    popoverShow.value = false;
  };
</script>

<style lang="less" scoped>
.batch-edit {
  .batch-edit-trigger {
    margin-left: 5px;
    color: @primary-color;
    cursor: pointer;
  }

  .batch-edit-content {
    padding: 9px 2px;
  }

  .batch-edit-header {
    padding-bottom: 16px;
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
      position: relative;
      margin: 12px 0 16px;

      &::before {
        position: absolute;
        top: -4px;
        left: var(--offset);
        width: 6px;
        height: 6px;
        background-color: @white-color;
        border: 1px solid transparent;
        border-top-color: @border-light-gray;
        border-left-color: @border-light-gray;
        content: "";
        transform: rotateZ(45deg);
      }

      &.is-focused {
        &::before {
          border-top-color: @border-primary;
          border-left-color: @border-primary;
        }
      }
    }

    .batch-edit-error {
      position: absolute;
      bottom: -4px;
      left: 0;
      font-size: @font-size-mini;
      color: @danger-color;
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
