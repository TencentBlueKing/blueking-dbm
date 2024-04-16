<template>
  <BkPopConfirm
    :is-show="isShow"
    trigger="manual"
    width="395"
    @cancel="() => isShow = false"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="batch-edit-column-select">
        <div class="main-title">
          {{ t('批量编辑') }}{{ title }}
        </div>
        <div
          class="title-spot edit-title"
          style="font-weight: normal;">
          {{ title }} <span class="required" />
        </div>
        <BkSelect
          v-if="type === 'select'"
          v-model="localValue"
          :clearable="false"
          filterable
          :list="dataList" />
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts" generic="T extends string | number">
  import { useI18n } from 'vue-i18n';

  interface Props {
    title: string;
    dataList?: {
      value: T,
      label: string,
    }[];
    type?: 'select'
  }

  interface Emits {
    (e: 'change', value: string): void,
  }

  withDefaults(defineProps<Props>(), {
    dataList: () => ([]),
    type: 'select',
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();

  const localValue = ref('');

  const handleConfirm = () => {
    emits('change', localValue.value);
    isShow.value = false;
  };
</script>

  <style lang="less">
  .batch-edit-column-select {
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
