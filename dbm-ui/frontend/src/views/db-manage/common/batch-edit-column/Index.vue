<template>
  <BkPopConfirm
    :is-show="isShow"
    trigger="manual"
    width="395"
    @after-show="handleAfterShow"
    @cancel="() => (isShow = false)"
    @confirm="handleConfirm">
    <span>
      <slot />
    </span>
    <template #content>
      <div class="batch-edit-column-select">
        <div class="main-title">{{ titlePrefixTypeMap[titlePrefixType] }}{{ title }}</div>
        <slot name="content">
          <div>
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
              ref="inputRef"
              v-model="localValue"
              :placeholder="placeholder"
              :rows="5"
              type="textarea"
              @change="handleChange" />
            <BkInput
              v-else-if="type === 'input'"
              :disabled="disabled"
              :model-value="localValue"
              @change="handleChange" />
            <BkInput
              v-else-if="type === 'number-input'"
              :disabled="disabled"
              :model-value="localValue"
              type="number"
              @change="handleChange" />
            <BkTagInput
              v-else-if="type === 'taginput'"
              allow-auto-match
              allow-create
              :disabled="disabled"
              has-delete-icon
              :model-value="localValue"
              :paste-fn="tagInputPasteFn"
              @change="handleChange" />
            <BkDatePicker
              v-else-if="type === 'datetime'"
              :clearable="false"
              :disabled="disabled"
              :disabled-date="disableFn"
              :model-value="localValue"
              type="datetime"
              @change="handleChange">
            </BkDatePicker>
          </div>
        </slot>
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  interface Props {
    title: string;
    dataList?: {
      value: string | number;
      label: string;
    }[];
    type?: 'select' | 'textarea' | 'input' | 'taginput' | 'datetime' | 'number-input';
    placeholder?: string;
    disableFn?: (date?: Date | number) => boolean;
    titlePrefixType?: 'edit' | 'entry';
  }

  interface Emits {
    (e: 'change', value: UnwrapRef<typeof localValue>): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dataList: () => [],
    type: 'select',
    placeholder: '',
    disableFn: () => false,
    titlePrefixType: 'edit',
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
  });
  // const slots = useSlots();

  const { t } = useI18n();

  const titlePrefixTypeMap = {
    edit: t('统一设置'),
    entry: t('批量录入'),
  };

  const inputRef = ref();
  const localValue = ref<string | string[]>(props.type === 'taginput' ? [] : '');

  const disabled = computed(() => props.disableFn());

  watch(
    () => props.dataList,
    () => {
      localValue.value = '';
    },
  );

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));

  const handleChange = (value: UnwrapRef<typeof localValue>) => {
    localValue.value = value;
  };

  const handleConfirm = () => {
    if (props.type === 'taginput') {
      // 组件内为200ms后失焦处理失焦的回调，这里将任务添加至失焦回调后，以获取最新值
      setTimeout(() => {
        handleConfirmChange();
      }, 210);
    } else {
      handleConfirmChange();
    }
  };

  const handleConfirmChange = () => {
    emits('change', localValue.value);
    isShow.value = false;
  };

  const handleAfterShow = () => {
    if (props.type === 'textarea') {
      nextTick(() => {
        inputRef.value?.focus();
      });
    }
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
      margin-bottom: 20px;
      font-size: 16px;
      color: #313238;
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
