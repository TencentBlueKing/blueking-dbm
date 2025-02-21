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
        <span
          v-if="isEmpty"
          class="placehold">
          {{ t('请选择屏蔽的时间范围') }}
        </span>
        <span v-else>{{ displayValue }}</span>
      </div>
    </template>
  </BkDatePicker>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  interface Props {
    disabled?: boolean;
  }

  type Emits = (e: 'finish', value: [string, string]) => void;

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<[string, string]>({
    default: () => ['', ''],
  });

  const updateShortcutText = (data: { text: string }) => (shortcutText.value = data.text);

  const { t } = useI18n();

  const showPanel = ref(false);
  const isShortcut = ref(false);
  const shortcutText = ref('');

  const displayValue = computed(() => {
    if (isShortcut.value) {
      return `${shortcutText.value} (${modelValue.value.join('-')})`;
    }

    return modelValue.value.join('-');
  });

  const isEmpty = computed(() => modelValue.value.every((item) => !item));

  // TODO: 优化
  const dateShortCut = [
    {
      onClick: updateShortcutText,
      text: t('30分钟'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(start.getTime() + 1800 * 1000);
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('1小时'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(start.getTime() + 3600 * 1000);
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('12小时'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(start.getTime() + 3600 * 1000 * 12);
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('1天'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(start.getTime() + 3600 * 1000 * 24);
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('7天'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(start.getTime() + 3600 * 1000 * 24 * 7);
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('1个月'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(dayjs().add(1, 'month').valueOf());
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('3个月'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(dayjs().add(3, 'month').valueOf());
        return [start, end];
      },
    },
    {
      onClick: updateShortcutText,
      text: t('6个月'),
      value() {
        const end = new Date();
        const start = new Date();
        end.setTime(dayjs().add(6, 'month').valueOf());
        return [start, end];
      },
    },
  ];

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

  const handleDatePickerChange = (value: [string, string]) => {
    modelValue.value = value;
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
    }
  }

  .shield-date-picker-main {
    .shortcuts-item {
      padding-left: 16px !important;
      font-size: 12px;
    }
  }
</style>
