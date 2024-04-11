<template>
  <BkPopConfirm
    :is-show="isShow"
    trigger="manual"
    width="395"
    @cancel="() => isShow = false"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="db-backup-batch-edit-local">
        <div class="main-title">
          {{ t('批量编辑') }}{{ t('备份位置') }}
        </div>
        <div
          class="title-spot edit-title"
          style="font-weight: normal;">
          {{ t('备份位置') }} <span class="required" />
        </div>
        <BkSelect
          v-model="localValue"
          :clearable="false"
          filterable
          :list="localList" />
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'change', value: string): void,
  }

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();

  const localValue = ref('');

  const localList = [
    {
      value: 'master',
      label: 'master',
    },
    {
      value: 'slave',
      label: 'slave',
    },
  ];

  const handleConfirm = () => {
    emits('change', localValue.value);
    isShow.value = false;
  };
</script>

  <style lang="less">
  .db-backup-batch-edit-local {
    margin-bottom: 30px;

    & + .bk-pop-confirm-footer {
      button {
        width: 60px;
      }
    }
    .main-title {
      font-size: 16px;
      color: #313238;
      margin-bottom: 20px;
    }
    .edit-title {
      margin-bottom: 6px;
    }

    .input-box {
      height: 32px;
    }
  }
  </style>
