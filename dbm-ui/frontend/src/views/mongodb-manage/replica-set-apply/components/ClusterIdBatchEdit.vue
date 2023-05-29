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
    <BkButton
      class="ml-4"
      text
      theme="primary"
      @click="() => popoverShow = true">
      <DbIcon
        class="batch-edit-trigger"
        type="bulk-edit" />
    </BkButton>
    <template #content>
      <div class="batch-edit-content">
        <p class="batch-edit-header">
          {{ t('批量录入集群ID') }}
          <span>({{ t('通过换行分隔_快速批量编辑多个集群ID') }})</span>
        </p>
        <div class="batch-edit-box">
          <BkInput
            v-model="clusterId"
            class="batch-edit-input"
            :placeholder="t('以小写英文字母开头_且只能包含小写英文字母_数字_连字符_多个换行分隔')"
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

  import { nameRegx } from '@common/regex';

  interface Emits {
    (e: 'change', value: string[]): void
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const errorTextMap = {
    rule: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
    repeat: t('集群ID重复'),
    maxlength: t('最大长度为m', { m: 63 }),
  };

  const { body } = document;

  const popoverShow = ref(false);
  const clusterId = ref('');
  const errorShow = ref(false);
  const errorText = ref('');

  const textareaRows = computed(() => {
    const rows = clusterId.value.split('\n').length;
    if (rows <= 5) {
      return 5;
    }
    return rows > 10 ? 10 : rows;
  });

  watch(popoverShow, (show) => {
    if (show === false) {
      clusterId.value = '';
      errorShow.value = false;
    }
  });

  watch(() => clusterId.value, (value) => {
    value && handleValidate();
  });

  const handleValidate = () => {
    const newClusterIds = clusterId.value.split('\n');
    // 校验最大长度
    const maxlengthRes = newClusterIds.every(key => key.length <= 63);
    if (maxlengthRes === false) {
      errorText.value = errorTextMap.maxlength;
      errorShow.value = true;
      return false;
    }
    // 校验格式
    const validate = newClusterIds.every(key => nameRegx.test(key));
    if (!validate) {
      errorText.value = errorTextMap.rule;
      errorShow.value = !validate;
      return validate;
    }
    // 校验名称是否重复
    const uniqClusterIds = _.uniq(newClusterIds);
    const hasRepeat = newClusterIds.length !== uniqClusterIds.length;
    errorText.value = errorTextMap.repeat;
    errorShow.value = hasRepeat;
    return !hasRepeat;
  };

  const handleConfirm = () => {
    handleValidate();
    if (errorShow.value === true) {
      return;
    }

    emits('change', clusterId.value.split('\n'));
    handleCancel();
  };

  const handleCancel = () => {
    popoverShow.value = false;
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
      position: relative;
      margin: 12px 0;

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
