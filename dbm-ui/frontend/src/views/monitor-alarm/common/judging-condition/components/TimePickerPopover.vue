<template>
  <DbPopconfirm
    v-model:is-show="isShow"
    :confirm-handler="handleConfirm"
    :title="title"
    :width="320"
    @toggle-show="handleToggleShow">
    <slot />
    <template #content>
      <div class="time-picker-popover-content">
        <div class="time-bar-wrapper">
          <div class="time-bar-legend">
            <span class="legend-item">
              <span
                class="legend-dot"
                style="background: #2dcb56">
              </span>
              {{ t('当前选择') }}
            </span>
            <span class="legend-item">
              <span
                class="legend-dot"
                style="background: #3a84ff">
              </span>
              {{ t('已添加时段') }}
            </span>
          </div>
          <div class="time-bar">
            <div
              v-if="currentBarSegment.width !== '0'"
              class="time-bar-segment active-item"
              :style="currentBarSegment" />
            <div
              v-for="(item, index) in otherBarSegments"
              :key="index"
              class="time-bar-segment new-item"
              :style="item" />
          </div>
          <div class="time-bar-labels">
            <span>00:00</span>
            <span>04:00</span>
            <span>08:00</span>
            <span>12:00</span>
            <span>16:00</span>
            <span>20:00</span>
            <span>24:00</span>
          </div>
        </div>
        <div class="time-picker-row">
          <span class="picker-label">{{ t('开始时间') }}</span>
          <div class="time-picker-input-group">
            <BkInput
              v-model="localStartHour"
              class="time-picker-input"
              :max="23"
              :min="0"
              type="number"
              @change="updateTimeBar" />
            <span class="separator-mark">:</span>
            <BkInput
              v-model="localStartMinute"
              class="time-picker-input"
              :max="59"
              :min="0"
              type="number"
              @change="updateTimeBar" />
          </div>
        </div>
        <div class="time-picker-row">
          <span class="picker-label">{{ t('结束时间') }}</span>
          <div class="time-picker-input-group">
            <BkInput
              v-model="localEndHour"
              class="time-picker-input"
              :max="23"
              :min="0"
              type="number"
              @change="updateTimeBar" />
            <span class="separator-mark">:</span>
            <BkInput
              v-model="localEndMinute"
              class="time-picker-input"
              :max="59"
              :min="0"
              type="number"
              @change="updateTimeBar" />
          </div>
        </div>
        <div
          v-if="conflictTip"
          class="time-conflict-tip">
          {{ conflictTip }}
        </div>
      </div>
    </template>
  </DbPopconfirm>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { EMode } from './TimeRangePicker.vue';

  interface Props {
    currentIndex: number;
    mode: EMode;
    timeRanges: [string, string][];
  }

  interface Emits {
    (
      e: 'confirm',
      value: {
        endHour: number;
        endMinute: number;
        startHour: number;
        startMinute: number;
      },
    ): void;
    (e: 'close'): void;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<Emits>();

  const modelValue = defineModel<{
    endHour: number | string;
    endMinute: number | string;
    startHour: number | string;
    startMinute: number | string;
  }>({
    required: true,
  });
  const isShow = defineModel<boolean>('is-show', { required: true });

  const { t } = useI18n();

  const localStartHour = ref<number | string>('');
  const localStartMinute = ref<number | string>('');
  const localEndHour = ref<number | string>('');
  const localEndMinute = ref<number | string>('');
  const conflictTip = ref('');

  const title = computed(() => (props.mode === EMode.add ? t('添加生效时间段') : t('编辑生效时间段')));

  const startTimeMinutes = computed(() => {
    const hour = typeof localStartHour.value === 'string' ? parseInt(localStartHour.value) || 0 : localStartHour.value;
    const minute =
      typeof localStartMinute.value === 'string' ? parseInt(localStartMinute.value) || 0 : localStartMinute.value;
    return hour * 60 + minute;
  });

  const endTimeMinutes = computed(() => {
    const hour = typeof localEndHour.value === 'string' ? parseInt(localEndHour.value) || 0 : localEndHour.value;
    const minute =
      typeof localEndMinute.value === 'string' ? parseInt(localEndMinute.value) || 0 : localEndMinute.value;
    return hour * 60 + minute;
  });

  const currentBarSegment = computed(() => {
    if (startTimeMinutes.value >= endTimeMinutes.value) {
      return { left: '0', width: '0' };
    }
    const left = (startTimeMinutes.value / 1440) * 100;
    const width = ((endTimeMinutes.value - startTimeMinutes.value) / 1440) * 100;
    return { left: `${left}%`, width: `${width}%` };
  });

  const otherBarSegments = computed(() => {
    const segments: { left: string; width: string }[] = [];
    props.timeRanges.forEach((range, index) => {
      if (props.mode === EMode.edit && index === props.currentIndex) {
        return;
      }
      const start = parseTimeToMinutes(range[0]);
      const end = parseTimeToMinutes(range[1]);
      if (end > start) {
        const left = (start / 1440) * 100;
        const width = ((end - start) / 1440) * 100;
        segments.push({ left: `${left}%`, width: `${width}%` });
      }
    });
    return segments;
  });

  watch(
    modelValue,
    () => {
      localStartHour.value = modelValue.value.startHour;
      localStartMinute.value = modelValue.value.startMinute;
      localEndHour.value = modelValue.value.endHour;
      localEndMinute.value = modelValue.value.endMinute;
    },
    {
      immediate: true,
    },
  );

  watch(isShow, (val) => {
    if (val) {
      conflictTip.value = '';
    }
  });

  const parseTimeToMinutes = (time: string) => {
    if (time === '24:00') return 1440;
    const [hour, minute] = time.split(':').map(Number);
    return hour * 60 + minute;
  };

  const validateTimeRange = () => {
    const start = startTimeMinutes.value;
    const end = endTimeMinutes.value;
    if (start >= end) {
      return { isValid: false, message: t('结束时间必须大于开始时间') };
    }
    const allRanges = [...props.timeRanges];
    if (props.mode === EMode.edit) {
      allRanges.splice(props.currentIndex, 1);
    }
    const hasConflict = allRanges.some((range) => {
      const s1 = parseTimeToMinutes(range[0]);
      const e1 = parseTimeToMinutes(range[1]);
      const s2 = start;
      const e2 = end;
      return !(e2 <= s1 || s2 >= e1);
    });
    if (hasConflict) {
      return { isValid: false, message: t('时间段与现有时间段重叠') };
    }
    return { isValid: true };
  };

  const handleConfirm = async () => {
    const validation = validateTimeRange();
    if (!validation.isValid) {
      conflictTip.value = validation.message || '';
      return Promise.reject(new Error(validation.message));
    }
    conflictTip.value = '';
    emit('confirm', {
      endHour: Number(localEndHour.value),
      endMinute: Number(localEndMinute.value),
      startHour: Number(localStartHour.value),
      startMinute: Number(localStartMinute.value),
    });
    return Promise.resolve();
  };

  const handleToggleShow = (value: boolean) => {
    if (!value) {
      conflictTip.value = '';
      emit('close');
    }
  };

  const updateTimeBar = () => {
    conflictTip.value = '';
  };

  defineExpose({
    validateTimeRange,
  });
</script>

<style lang="less">
  .time-picker-popover-content {
    .time-bar-wrapper {
      margin-bottom: 12px;

      .time-bar-legend {
        display: flex;
        gap: 16px;
        justify-content: flex-end;
        margin-bottom: 4px;

        .legend-item {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 11px;
          color: #979ba5;

          .legend-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 2px;
            opacity: 60%;
          }
        }
      }

      .time-bar {
        position: relative;
        height: 20px;
        overflow: hidden;
        background: #f0f1f5;
        border-radius: 2px;

        .time-bar-segment {
          position: absolute;
          top: 0;
          bottom: 0;
          border-radius: 2px;
          transition: all 0.2s;

          &.active-item {
            background: #2dcb56;
            opacity: 60%;
          }

          &.new-item {
            background: #3a84ff;
            opacity: 60%;
          }
        }
      }

      .time-bar-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 4px;
        font-size: 10px;
        color: #979ba5;
      }
    }

    .time-picker-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;

      .picker-label {
        width: 48px;
        font-size: 12px;
        color: #63656e;
        flex-shrink: 0;
      }

      .time-picker-input-group {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;

        .time-picker-input {
          width: 100px;
          height: 32px;
          padding: 0 8px;
          font-size: 13px;
          color: #313238;
          text-align: center;
          border: 1px solid #c4c6cc;
          border-radius: 2px;
          outline: none;

          &:focus {
            border-color: #3a84ff;
          }
        }

        .separator-mark {
          font-size: 14px;
          color: #979ba5;
        }
      }
    }

    .time-conflict-tip {
      margin-bottom: 12px;
      font-size: 12px;
      color: #ea3636;
    }
  }
</style>
