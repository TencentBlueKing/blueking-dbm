<template>
  <BkDatePicker
    v-model="modelValue"
    class="shield-date-picker-main"
    :disabled="disabled"
    format="yyyy-MM-dd HH:mm:ss"
    :open="showPanel"
    :shortcuts="dateShortCut"
    style="width: 100%"
    type="datetimerange"
    use-shortcut-text
    @change="handleDatePickerChange"
    @open-change="handlePanelOpenChange"
    @shortcut-change="handleShortcutChange">
    <template #trigger>
      <div
        class="datetime-picker-trigger"
        :class="{
          'is-show-panel': showPanel,
          'is-disabled': disabled,
        }"
        @click="handleOpenPanel">
        <DbIcon
          class="date-icon"
          type="date-line" />
        <div
          v-if="isEmpty"
          class="placehold">
          {{ placeholder || t('请选择屏蔽的时间范围') }}
        </div>
        <div
          v-else
          class="display-input"
          :contenteditable="!disabled"
          @blur="handleDisplayValueChange">
          {{ displayValue }}
        </div>
        <DbIcon
          v-if="clearable && !isEmpty"
          class="close-icon"
          type="close-circle-shape"
          @click.stop="handleClearInput" />
      </div>
    </template>
  </BkDatePicker>
</template>
<script setup lang="ts">
  import dayjs, { type ManipulateType } from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import { isValidDateTime } from '@utils';

  interface Props {
    clearable?: boolean;
    disabled?: boolean;
    placeholder?: string;
  }

  interface Emits {
    (e: 'finish', value: [string, string]): void;
    (e: 'change', value: [string, string]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clearable: false,
    disabled: false,
    placeholder: '',
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<[string, string]>({
    default: () => ['', ''],
  });

  const updateShortcutText = (data: { text: string }) => (shortcutText.value = data.text);

  const getShortcutValue = (num: number, unit: ManipulateType) => {
    const end = new Date();
    const start = new Date();
    end.setTime(dayjs().add(num, unit).valueOf());
    return [start, end];
  };

  const { t } = useI18n();

  const showPanel = ref(false);
  const isShortcut = ref(false);
  const shortcutText = ref('');
  const displayValue = ref('');

  const isEmpty = computed(() => modelValue.value.every((item) => !item));

  const dateShortCut = [
    {
      onClick: updateShortcutText,
      text: t('n分钟', { n: 30 }),
      value: getShortcutValue(30, 'minute'),
    },
    {
      onClick: updateShortcutText,
      text: t('n小时', { n: 1 }),
      value: getShortcutValue(60, 'minute'),
    },
    {
      onClick: updateShortcutText,
      text: t('n小时', { n: 12 }),
      value: getShortcutValue(12, 'hour'),
    },
    {
      onClick: updateShortcutText,
      text: t('n天', { n: 1 }),
      value: getShortcutValue(1, 'day'),
    },
    {
      onClick: updateShortcutText,
      text: t('n天', { n: 7 }),
      value: getShortcutValue(7, 'day'),
    },
    {
      onClick: updateShortcutText,
      text: t('n个月', { n: 1 }),
      value: getShortcutValue(1, 'month'),
    },
    {
      onClick: updateShortcutText,
      text: t('n个月', { n: 3 }),
      value: getShortcutValue(3, 'month'),
    },
    {
      onClick: updateShortcutText,
      text: t('n个月', { n: 6 }),
      value: getShortcutValue(6, 'month'),
    },
  ] as any;

  watch(
    modelValue,
    () => {
      displayValue.value = modelValue.value.join('~');
    },
    {
      immediate: true,
    },
  );

  const handleClearInput = () => {
    modelValue.value = ['', ''];
    emits('change', modelValue.value);
  };

  const handleOpenPanel = () => {
    if (props.disabled) {
      return;
    }

    showPanel.value = true;
  };

  const handleShortcutChange = (value: string) => {
    isShortcut.value = !!value;
  };

  const handlePanelOpenChange = (isOpen: boolean) => {
    showPanel.value = isOpen;
    if (!isOpen) {
      emits('finish', modelValue.value);
    }
  };

  const handleDisplayValueChange = (event: any) => {
    const inputValue = event.target.innerText as string;
    displayValue.value = inputValue;
    nextTick(() => {
      if (inputValue.includes('~')) {
        const dates = inputValue.split('~') as [string, string];
        if (dates.every((date) => isValidDateTime(date))) {
          modelValue.value = dates;
          return;
        }
      }

      displayValue.value = modelValue.value.join('~');
    });
  };

  const handleDatePickerChange = (value: [string, string]) => {
    modelValue.value = value;
    emits('change', modelValue.value);
  };
</script>
<style lang="less">
  .datetime-picker-trigger {
    display: flex;
    width: 100%;
    height: 32px;
    padding: 0 10px;
    font-size: 12px;
    cursor: pointer;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    align-items: center;

    &.is-show-panel {
      border: 1px solid #3a84ff;
    }

    &.is-disabled {
      color: #c4c6cc;
      cursor: not-allowed;
      background-color: #fafbfd;
      border-color: #c4c6cc;

      .date-icon {
        color: #c4c6cc;
      }
    }

    .date-icon {
      margin-right: 8px;
      font-size: 16px;
    }

    .placehold {
      color: #c4c6cc;
      flex: 1;
    }

    .display-input {
      display: flex;
      height: 32px;
      outline: none;
      align-items: center;
      flex: 1;
    }

    .close-icon {
      margin-left: 5px;
      font-size: 12px;
      color: #c4c6cc;
      cursor: pointer;

      &:hover {
        color: #979ba5;
      }
    }
  }

  .shield-date-picker-main {
    .shortcuts-item {
      padding-left: 16px !important;
      font-size: 12px;
    }
  }
</style>
