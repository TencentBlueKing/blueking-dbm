<template>
  <div class="edit-series-main">
    <div
      v-if="isEdit"
      class="edit-main">
      <div
        class="edit-input-main"
        :class="{ 'is-error': errorMessage }">
        <BkInput
          ref="editInputRef"
          v-model="newVersionName"
          v-bk-tooltips="t('同一版本系列（如 5.7.20）代表核心功能兼容，支持原地升级')"
          class="edit-input"
          :placeholder="t('请输入版本系列名称')"
          @click.stop
          @enter="handleConfirmAdd" />
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
          @click.stop="() => (isEdit = false)" />
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

  import { messageSuccess } from '@utils';

  interface Props {
    data?: string;
    distributionId: number;
    mode?: 'create' | 'update';
    seriesId?: number;
  }

  type Emits = (e: 'confirm', id: number, name: string) => void;

  interface Slots {
    default?: () => any;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
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
    messageSuccess(props.mode === 'create' ? t('新增成功') : t('更新成功'));
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

  const handleConfirmAdd = () => {
    if (newVersionName.value.trim() === '') {
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
      padding: 0 12px;
      align-items: center;

      .edit-input-main {
        flex: 1;
        position: relative;

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
