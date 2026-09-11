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
  <div class="edit-series-main">
    <div
      v-if="isEdit"
      class="edit-main">
      <div
        class="edit-input-main"
        :class="{ 'is-error': errorMessage, 'is-empty': !newVersionName }">
        <BkInput
          ref="editInputRef"
          v-model="newVersionName"
          class="edit-input"
          :placeholder="t('请输入xx', [t('系列名')])"
          @click.stop
          @enter="handleConfirmAdd"
          @input="() => (errorMessage = '')" />
        <DbIcon
          v-bk-tooltips="errorMessage"
          class="error-icon"
          type="exclamation-fill" />
      </div>
      <div class="operation-main">
        <DbIcon
          class="confirm-icon"
          type="check-line"
          @click.stop="handleConfirmAdd" />
        <DbIcon
          class="cancel-icon"
          type="close"
          @click.stop="handleCancelEdit" />
      </div>
    </div>
    <div
      v-else
      @click="() => (isEdit = true)">
      <slot />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createVersionSeries, updateVersionSeries } from '@services/source/version';

  import { CHINESE_CHAR_REG, IDENTIFIER_NAME_REG } from '@views/version-files/v2/common';

  import { messageSuccess } from '@utils';

  interface Props {
    data?: string;
    distributionId?: number;
    existedList?: string[];
    mode?: 'create' | 'update';
    seriesId?: number;
  }

  type Emits = (e: 'confirm', id: number, name: string) => void;

  interface Slots {
    default?: () => any;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    distributionId: 0,
    existedList: () => [],
    mode: 'create',
    seriesId: undefined,
  });
  const emits = defineEmits<Emits>();

  defineSlots<Slots>();

  const isEdit = defineModel<boolean>('isEdit', {
    default: false,
  });

  const { t } = useI18n();

  const editInputRef = ref();
  const newVersionName = ref('');
  const errorMessage = ref('');

  watch(
    () => props.data,
    () => {
      newVersionName.value = props.data || '';
    },
    {
      immediate: true,
    },
  );
  const handleSuccess = (data: { id: number; name: string }) => {
    emits('confirm', data.id, data.name);
    messageSuccess(t('操作成功'));
    isEdit.value = false;
    newVersionName.value = '';
  };

  const { run: runCreateVersionSeries } = useRequest(createVersionSeries, {
    manual: true,
    onSuccess: handleSuccess,
  });

  const { run: runUpdateVersionSeries } = useRequest(updateVersionSeries, {
    manual: true,
    onSuccess: handleSuccess,
  });

  watch(
    isEdit,
    () => {
      if (isEdit.value) {
        setTimeout(() => {
          editInputRef.value.focus();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleCancelEdit = () => {
    errorMessage.value = '';
    newVersionName.value = '';
    isEdit.value = false;
  };

  const handleConfirmAdd = () => {
    const oldValidName = props.data.toLocaleLowerCase();
    const newValidName = newVersionName.value.toLocaleLowerCase();
    if (newVersionName.value.trim() === '' || oldValidName === newValidName) {
      return;
    }

    if (CHINESE_CHAR_REG.test(newVersionName.value)) {
      errorMessage.value = t('请勿使用中文');
      return;
    }

    if (!IDENTIFIER_NAME_REG.test(newVersionName.value)) {
      errorMessage.value = t('格式不正确，请勿使用空格或特殊符号');
      return;
    }

    if (props.existedList.includes(newValidName) && oldValidName !== newValidName) {
      errorMessage.value = t('该系列名已存在');
      return;
    }

    if (props.mode === 'create') {
      runCreateVersionSeries({
        distribution: props.distributionId,
        name: newVersionName.value,
      });
    } else {
      runUpdateVersionSeries({
        distribution: props.distributionId,
        id: props.seriesId!,
        name: newVersionName.value,
      });
    }
  };
</script>
<style lang="less">
  .edit-series-main {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;

    .edit-main {
      display: flex;
      width: 100%;
      align-items: center;
      padding: 0 12px;

      .edit-input-main {
        flex: 1;
        position: relative;

        &.is-empty {
          .edit-input {
            border-color: #ea3636;
          }
        }

        &.is-error {
          .edit-input {
            border-color: #ea3636;

            .bk-input--text {
              padding-right: 28px;
            }
          }

          .error-icon {
            position: absolute;
            top: 50%;
            right: 8px;
            display: block;
            font-size: 14px;
            color: #ea3636;
            cursor: pointer;
            transform: translateY(-50%);
          }
        }

        .error-icon {
          display: none;
        }

        .edit-input {
          width: 100%;
        }
      }

      .operation-main {
        display: flex;
        margin-left: 8px;
        cursor: pointer;
        align-items: center;
        justify-content: center;
        gap: 4px;

        .confirm-icon {
          font-size: 16px;
          color: #2caf5e;
        }

        .cancel-icon {
          font-size: 20px;
          color: #c4c6cc;
        }
      }
    }
  }
</style>
