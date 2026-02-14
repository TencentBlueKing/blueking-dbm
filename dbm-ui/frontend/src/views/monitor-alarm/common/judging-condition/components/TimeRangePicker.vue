<template>
  <div class="time-range-picker">
    <div class="time-range-container">
      <template v-if="disabled">
        <BkTag
          v-for="(item, index) in localValue"
          :key="index"
          class="time-tag"
          type="stroke">
          <DbIcon
            class="mr-4"
            type="time" />
          <span>
            <span>{{ handleFormatTime(item[0]) }}</span>
            <span>-</span>
            <span>{{ handleFormatTime(item[1]) }}</span>
          </span>
        </BkTag>
      </template>
      <template v-else>
        <TimePickerPopover
          v-for="(item, index) in localValue"
          :key="index"
          v-model="timePickerModel"
          v-model:is-show="isShow"
          :current-index="currentIndex"
          :mode="mode"
          :time-ranges="localValue"
          @close="closeTimePicker"
          @confirm="handleTimePickerConfirm">
          <BkTag
            v-bk-tooltips="{
              content: t('点击编辑'),
              disabled: disabled || currentIndex === index,
            }"
            class="time-tag editable-tag"
            :class="{ editing: currentIndex === index && isShow }"
            :closable="!disabled && localValue.length > 1"
            type="stroke"
            @click="(evt: MouseEvent) => handleClickItem(evt, index)"
            @close="() => handleCloseItem(index)">
            <DbIcon
              class="mr-4"
              type="time" />
            <span>
              <span>{{ handleFormatTime(item[0]) }}</span>
              <span>-</span>
              <span>{{ handleFormatTime(item[1]) }}</span>
            </span>
          </BkTag>
        </TimePickerPopover>
        <TimePickerPopover
          v-model="timePickerModel"
          v-model:is-show="isShow"
          :current-index="currentIndex"
          :mode="mode"
          :time-ranges="localValue"
          @close="closeTimePicker"
          @confirm="handleTimePickerConfirm">
          <BkButton
            class="time-add-btn"
            :disabled="!isAllowAdd"
            size="small"
            text
            @click="handleAddTimeRange">
            <DbIcon
              class="mr-4"
              type="add" />
            {{ t('添加时间段') }}
          </BkButton>
        </TimePickerPopover>
      </template>
    </div>
    <div
      v-if="!disabled"
      class="time-range-tip">
      {{ timeCoverageTip }}
    </div>
  </div>
</template>

<script lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TimePickerPopover from './TimePickerPopover.vue';

  export enum EMode {
    add = 'add',
    edit = 'edit',
  }

  interface Props {
    disabled?: boolean;
  }
</script>
<script setup lang="ts">
  type TimeRange = [string, string];

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const emit = defineEmits<{
    change: [value: Array<TimeRange>];
  }>();

  const modelValue = defineModel<Array<TimeRange>>({
    default: () => [],
    required: true,
  });

  const { t } = useI18n();

  const isShow = ref(false);
  const mode = ref<EMode>(EMode.add);
  const currentIndex = ref(0);
  const localValue = ref<Array<TimeRange>>([]);
  const timePickerModel = ref({
    endHour: '23' as number | string,
    endMinute: '59' as number | string,
    startHour: '00' as number | string,
    startMinute: '00' as number | string,
  });

  const timeCoverageTip = computed(() => {
    const totalMinutes = calcCoveredMinutes();
    if (totalMinutes >= 1440) {
      return t('已覆盖 24 小时，全天生效');
    }
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    let tip = t('已覆盖 ');
    if (hours > 0) {
      tip += `${hours}${t(' 小时 ')}`;
    }
    if (minutes > 0) {
      tip += `${minutes}${t(' 分钟')}`;
    }
    tip += t('，剩余时段可继续添加');
    return tip;
  });

  const isAllowAdd = computed(() => {
    const totalMinutes = calcCoveredMinutes();
    return totalMinutes < 1440;
  });

  watch(
    () => modelValue.value,
    () => {
      localValue.value = _.cloneDeep(modelValue.value);
    },
    { immediate: true },
  );

  const calcCoveredMinutes = () => {
    const minutes = Array.from({ length: 24 * 60 }, () => false);
    localValue.value.forEach((range) => {
      const start = parseTimeToMinutes(range[0]);
      let end = parseTimeToMinutes(range[1]);
      if (range[1] === '23:59') {
        end = 1440;
      }
      for (let i = start; i < end; i++) {
        minutes[i] = true;
      }
    });
    return minutes.filter(Boolean).length;
  };

  const parseTimeToMinutes = (time: string) => {
    if (time === '24:00') {
      return 1440;
    }
    const [hour, minutes] = time.split(':').map(Number);
    return hour * 60 + minutes;
  };

  const formatTimeFromMinutes = (minutes: number) => {
    if (minutes >= 1440) {
      return '24:00';
    }
    const hour = Math.floor(minutes / 60);
    const minute = minutes % 60;
    return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  };

  const findFirstGap = () => {
    const minutes = Array.from({ length: 1440 }, () => false);
    localValue.value.forEach((range) => {
      const s = parseTimeToMinutes(range[0]);
      const e = parseTimeToMinutes(range[1]);
      for (let i = s; i < e; i++) minutes[i] = true;
    });
    let gapStart = -1;
    for (let i = 0; i < 1440; i++) {
      if (!minutes[i]) {
        if (gapStart === -1) gapStart = i;
      } else if (gapStart !== -1) {
        return { end: i, start: gapStart };
      }
    }
    if (gapStart !== -1) {
      return { end: 1440, start: gapStart };
    }
    return { end: 1440, start: 0 };
  };

  const handleClickItem = (event: MouseEvent, index: number) => {
    if (props.disabled) {
      event.preventDefault();
      event.stopPropagation();
      isShow.value = false;
      return;
    }
    mode.value = EMode.edit;
    currentIndex.value = index;
    const range = localValue.value[index];
    const [sH, sM] = range[0].split(':');
    const [eH, eM] = range[1].split(':');
    timePickerModel.value = {
      endHour: parseInt(eH),
      endMinute: parseInt(eM),
      startHour: parseInt(sH),
      startMinute: parseInt(sM),
    };
    isShow.value = true;
  };

  const handleCloseItem = (index: number) => {
    if (props.disabled || localValue.value.length <= 1) return;
    localValue.value.splice(index, 1);
    emit('change', localValue.value);
    modelValue.value = localValue.value;
  };

  const handleAddTimeRange = () => {
    if (props.disabled || !isAllowAdd.value) {
      return;
    }
    mode.value = EMode.add;
    currentIndex.value = localValue.value.length;
    const gap = findFirstGap();
    const start = gap.start;
    const end = gap.end === 1440 ? gap.end - 1 : gap.end;
    timePickerModel.value = {
      endHour: Math.floor(end / 60),
      endMinute: end % 60,
      startHour: Math.floor(start / 60),
      startMinute: start % 60,
    };
    isShow.value = true;
  };

  const handleTimePickerConfirm = ({
    endHour,
    endMinute,
    startHour,
    startMinute,
  }: {
    endHour: number;
    endMinute: number;
    startHour: number;
    startMinute: number;
  }) => {
    const start = formatTimeFromMinutes(startHour * 60 + startMinute);
    const end = formatTimeFromMinutes(endHour * 60 + endMinute);
    const newRange: TimeRange = [start, end];
    if (mode.value === EMode.add) {
      localValue.value.push(newRange);
    } else {
      localValue.value[currentIndex.value] = newRange;
    }
    modelValue.value = localValue.value;
    isShow.value = false;
  };

  const closeTimePicker = () => {
    isShow.value = false;
    currentIndex.value = 0;
  };

  const handleFormatTime = (time: string) => {
    if (!time) {
      return '';
    }
    const timeList = time.split(':');
    const [hour, minute] = timeList;
    return `${hour}:${minute}`;
  };
</script>

<style lang="less" scoped>
  .time-range-picker {
    position: relative;
  }

  .time-range-container {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    min-height: 32px;
  }

  .time-tag {
    height: 32px;
    user-select: none;

    &.editable-tag {
      cursor: pointer;
      transition: all 0.2s;
    }

    &:hover {
      background-color: #e6f0ff;
      border-color: #a3c5fd;
    }

    &.editing {
      color: #3a84ff;
      background-color: #e6f0ff;
      border-color: #3a84ff;
    }
  }

  .time-add-btn {
    height: 32px;
    padding: 0 12px;
    color: #3a84ff;
    border: 1px dashed #c4c6cc;
    border-radius: 2px;
    transition: all 0.2s;

    &:hover {
      background-color: #f0f5ff;
      border-color: #3a84ff;
    }

    &:disabled {
      color: #c4c6cc;
      cursor: not-allowed;
      background: #fafbfd;
      border-color: #dcdee5;
    }
  }

  .time-range-tip {
    // margin-top: 8px;
    font-size: 12px;
    color: #979ba5;
  }
</style>
