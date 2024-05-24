<template>
  <BkPopConfirm
    :is-show="isShow"
    trigger="manual"
    width="395"
    @cancel="() => (isShow = false)"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="batch-edit-column-select">
        <div class="main-title">{{ t('统一设置') }}{{ title }}</div>
        <div
          class="title-spot edit-title"
          style="font-weight: normal">
          {{ title }} <span class="required" />
        </div>
        <BkSelect
          v-if="type === 'select'"
          :clearable="false"
          :disabled="disabled"
          filterable
          :list="dataList"
          :model-value="localValue"
          @change="handleChange" />
        <BkInput
          v-else-if="type === 'textarea'"
          :model-value="localValue as string"
          :placeholder="placeholder"
          :rows="5"
          type="textarea"
          @change="handleChange" />
        <BkInput
          v-else-if="type === 'input'"
          :disabled="disabled"
          :model-value="localValue as string"
          @change="handleChange" />
        <BkInput
          v-else-if="type === 'number-input'"
          :disabled="disabled"
          :model-value="localValue as string"
          type="number"
          @change="handleChange" />
        <BkTagInput
          v-else-if="type === 'taginput'"
          allow-create
          :disabled="disabled"
          has-delete-icon
          :model-value="localValue as string[]"
          @change="handleChange" />
        <BkDatePicker
          v-else-if="type === 'datetime'"
          :clearable="false"
          :disabled="disabled"
          :disabled-date="disableFn"
          :model-value="localValue as string"
          type="datetime"
          @change="handleChange">
        </BkDatePicker>
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    title: string;
    dataList?: {
      value: string | number;
      label: string;
    }[];
    type?: 'select' | 'textarea' | 'input' | 'taginput' | 'datetime' | 'number-input';
    placeholder?: string;
    disableFn?: (date?: Date | number) => boolean;
  }

  interface Emits {
    (e: 'change', value: UnwrapRef<typeof localValue>): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dataList: () => [],
    type: 'select',
    placeholder: '',
    disableFn: () => false,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();

  const localValue = ref<string | string[]>(props.type === 'taginput' ? [] : '');

  const disabled = computed(() => props.disableFn());

  const handleChange = (value: UnwrapRef<typeof localValue>) => {
    localValue.value = value;
  };

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

    .bk-textarea {
      resize: none;
    }
  }
</style>
