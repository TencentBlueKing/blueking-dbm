<template>
  <div
    v-bk-tooltips="{
      placement: 'top',
      content: t('暂无可选时间段'),
      delay: 200,
      disabled: isAllowAdd,
    }"
    class="time-picker-multiple-wrap"
    @click="handleAddTimeRange">
    <DbIcon
      class="icon-mc-time"
      type="time" />
    <ul
      ref="timeRangeListRef"
      class="time-range-list">
      <li
        v-for="(item, index) in localValue"
        :key="index"
        class="time-range-item"
        :class="{ 'no-empty-time': disabled || (!isAllowAdd && index === localValue.length - 1) }"
        @click.stop="handleClickItem($event, index)">
        <span v-if="!(currentIndex === index && isShow)">
          <span>{{ handleFormatTime(item[0]) }}</span>
          <span>-</span>
          <span>{{ handleFormatTime(item[1]) }}</span>
        </span>
      </li>
      <li
        ref="triggerInputRef"
        class="trigger-input-wrap"
        :class="{ 'hide-second': format === 'HH:mm' }"
        :style="{ display: isShow ? '' : 'none' }"
        @click.stop>
        <BkTimePicker
          ref="timePickerRef"
          v-model="timeRange"
          allow-cross-day
          ext-popover-cls="time-range-multiple-popover"
          :format="format"
          :open="isShow"
          type="timerange">
          <template #trigger>
            <input
              ref="inputRef"
              v-model="triggerInputText"
              class="trigger-input"
              @blur="handleTimeRangeInputBlur"
              @focus="isFocus = true"
              @input="handleTimeRangeInput"
              @keydown.delete="handleDelItem" />
          </template>
        </BkTimePicker>
      </li>
    </ul>
    <span
      v-if="!localValue.length && !isShow"
      class="placeholder">
      {{ placeholder || t('选择时间范围') }}
    </span>
    <DbIcon
      v-if="!disabled && localValue.length"
      class="icon-mc-close-fill"
      type="delete-fill"
      @mousedown.stop="handleClearAll" />
  </div>
</template>

<script setup lang="ts">
  // import dayjs from 'dayjs';
  import _ from 'lodash';
  import { computed, nextTick, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { messageError, messageWarn } from '@utils';

  type TimeRange = [string, string];
  type ITimeValue = `${string}:${string}:${string}` | string;

  interface Props {
    // allowNextFocus?: boolean;
    // autoSort?: boolean;
    disabled: boolean;
    format?: 'HH:mm' | 'HH:mm:ss';
    // eslint-disable-next-line vue/require-default-prop
    placeholder?: string;
  }

  type Emits = (e: 'change', value: Array<TimeRange>) => void;

  const props = withDefaults(defineProps<Props>(), {
    format: 'HH:mm',
  });
  const emit = defineEmits<Emits>();
  const modelValue = defineModel<Array<TimeRange>>({ required: true });

  const END_TIME = '23:59:59';
  const START_TIME = '00:00:00';
  const TIME_FORMAT_REG = /HH|mm|ss/g;

  enum EMode {
    add = 'add',
    edit = 'edit',
  }

  const { t } = useI18n();

  const timeRangeListRef = useTemplateRef('timeRangeListRef');
  const triggerInputRef = useTemplateRef('triggerInputRef');
  const inputRef = useTemplateRef('inputRef');
  const timePickerRef = useTemplateRef('timePickerRef');

  const isShow = ref(false);
  const targetEl = ref<Element | null>(null);
  const mode = ref<EMode>(EMode.add);
  const triggerInputText = ref('');
  const currentIndex = ref(0);
  const timeRange = ref<TimeRange>(['', '']);
  const localValue = ref<Array<TimeRange>>([]);
  const isCustomTimeRange = ref(false);
  const isClearAll = ref(false);
  const isFocus = ref(false);

  const isAllowAdd = computed(() => {
    return localValue.value.length ? !!defaultAddTimeRange(localValue.value).length : true;
  });

  watch(
    () => modelValue.value,
    () => {
      localValue.value = _.cloneDeep(modelValue.value);
    },
    { immediate: true },
  );

  watch(isShow, () => {
    if (isShow.value) {
      isCustomTimeRange.value = false;
    } else {
      if (!isCustomTimeRange.value) {
        handleSubmit();
      }
      setTimeout(() => {
        isClearAll.value = false;
        isFocus.value = false;
      }, 200);
    }
  });

  const numberToStr = (number: number) => {
    if (number === 0) {
      return '00';
    }
    if (number < 10) {
      return `0${number}`;
    }
    return `${number}`;
  };

  const timeTransform = (timeValue: number | string | unknown, isToStr = false, minIsMinute = false) => {
    if (isToStr) {
      if (minIsMinute) {
        const one = Math.floor(Number(timeValue) / 60);
        const two = Math.floor(Number(timeValue) - one * 60);
        return `${numberToStr(one)}:${numberToStr(two)}`;
      }
      const one = Math.floor(Number(timeValue) / 3600);
      const two = Math.floor((Number(timeValue) - one * 3600) / 60);
      const three = Math.floor(Number(timeValue) - one * 3600 - two * 60);
      return `${numberToStr(one)}:${numberToStr(two)}:${numberToStr(three)}`;
    }
    return (timeValue as ITimeValue).split(':').reduce<number>((acc, cur, index) => {
      const time = Number(cur);
      let total = acc;
      if (minIsMinute) {
        if (index === 0) {
          total += time * 60;
        }
        if (index === 1) {
          total += time;
        }
      } else {
        if (index === 0) {
          total += time * 60 * 60;
        }
        if (index === 1) {
          total += time * 60;
        }
        if (index === 2) {
          total += time;
        }
      }
      return total;
    }, 0);
  };

  // 时间段重叠校验
  const timeRangeValidate = (allData: string[][], targetData: string[]) => {
    const oneDay = 24 * 60 * 60;
    const allDataTimeNumArr = allData.map((item) => {
      const one = timeTransform(item[0]);
      const two = timeTransform(item[1]);
      if (one > two) {
        // 跨天
        return [one, Number(two) + oneDay];
      }
      // 不跨天
      return [one, two];
    });
    const one = timeTransform(targetData[0]) as number;
    const two = timeTransform(targetData[1]) as number;
    let targetDataTimeNumberArr: number[] = [];
    if (one > two) {
      // 跨天
      targetDataTimeNumberArr = [one, Number(two) + oneDay];
    } else {
      targetDataTimeNumberArr = [one, two];
    }
    const start = targetDataTimeNumberArr[0];
    const end = targetDataTimeNumberArr[1];
    return allDataTimeNumArr.every((item) => {
      const itemStart = item[0] as number;
      const itemEnd = item[1] as number;
      if (itemEnd > oneDay) {
        return start > itemEnd - oneDay && end < itemStart;
      }
      // 非跨天
      return (
        (start < itemStart && end < itemStart) ||
        (start > itemEnd && (end > oneDay ? end - oneDay < itemStart : end > itemEnd))
      );
    });
  };

  // 新增默认时间段
  const defaultAddTimeRange = (allData: string[][], minIsMinute = true) => {
    const oneDay = minIsMinute ? 24 * 60 : 24 * 60 * 60;
    const alllDataNum: number[][] = [];
    // 转换成秒
    allData.forEach((item) => {
      const one = timeTransform(item[0], false, minIsMinute) as number;
      const two = timeTransform(item[1], false, minIsMinute) as number;
      if (one > two) {
        // 跨天的时间段分成连个时间段
        const oneArr = [0, two];
        const twoArr = [one, oneDay - 1];
        alllDataNum.push(oneArr);
        alllDataNum.push(twoArr);
      } else {
        alllDataNum.push([one, two]);
      }
    });
    // 按起始时间排序
    const allDataSort = alllDataNum.sort((a, b) => a[0] - b[0]);
    // 从第一开始查找间隔
    const allInterval: number[][] = [];
    allDataSort.reduce<number[]>((acc, cur, index) => {
      const one = acc;
      const two = cur;
      if (allDataSort.length > 1) {
        if (index > 0) {
          const isHasInterval = two[0] - one[1] > 2;
          if (one[0] > 2 && index === 1) {
            // 当第一起始时间段大于2
            allInterval.push([0, one[0] - 1]);
          }
          if (isHasInterval) {
            // 当包含间隔时
            allInterval.push([one[1] + 1, two[0] - 1]);
          }
          if (index === allDataSort.length - 1 && two[1] < oneDay - 2) {
            // 当最后一个时
            allInterval.push([two[1] + 1, oneDay - 1]);
          }
        }
      } else {
        const one = allDataSort[0][0];
        const two = allDataSort[0][1];
        if (one > 2) {
          allInterval.push([0, one - 1]);
        }
        if (two < oneDay - 2) {
          allInterval.push([two + 1, oneDay - 1]);
        }
      }
      return cur;
    }, []);
    return allInterval.map((item) => [
      timeTransform(item[0], true, minIsMinute),
      timeTransform(item[1], true, minIsMinute),
    ]) as string[][];
  };

  /**
   * 新增时间范围
   */
  const handleAddTimeRange = () => {
    if (props.disabled) {
      return;
    }
    if (isShow.value || isFocus.value) {
      return;
    }
    mode.value = EMode.add;
    targetEl.value = null;
    timeRange.value = handleCreateTimeRange();
    if (!timeRange.value) {
      return;
    }
    currentIndex.value = localValue.value.length;
    localValue.value.push([...timeRange.value]);
    handleMoveTrigger(true);
    nextTick(() => {
      isShow.value = true;
    });
  };

  /**
   * 根据当前空闲时间段自动生成可选的时间段
   */
  const handleCreateTimeRange = () => {
    let timeRange: [string, string] | null = null;
    if (!localValue.value.length) {
      timeRange = [START_TIME, END_TIME];
    } else {
      const timeRanges = defaultAddTimeRange(localValue.value) as [string, string][];
      timeRange = timeRanges?.[0] || null;
    }
    return timeRange;
  };

  /**
   * 点击选中某个时间段
   * @param evt 点击事件
   * @param index 目标索引
   */
  const handleClickItem = (evt: MouseEvent, index: number) => {
    if (props.disabled) {
      return;
    }
    mode.value = EMode.edit;
    targetEl.value = evt.currentTarget as Element;
    timeRange.value = localValue.value[index];
    currentIndex.value = index;
    handleMoveTrigger();
    setTimeout(() => {
      isShow.value = true;
      inputFocus();
    }, 100);
  };

  const inputFocus = () => {
    setTimeout(() => {
      inputRef.value?.focus();
    }, 50);
  };

  /**
   * 删除一个时间范围
   */
  const handleDelItem = _.debounce(() => {
    if (triggerInputText.value.length > 0) return;
    localValue.value.splice(currentIndex.value, 1);
    if (currentIndex.value) {
      currentIndex.value -= 1;
      targetEl.value = timeRangeListRef.value?.children[currentIndex.value] || null;
      timeRange.value = [...localValue.value[currentIndex.value]];
      nextTick(() => {
        handleMoveTrigger();
      });
      setTimeout(() => {
        isShow.value = true;
        inputFocus();
      }, 300);
    } else {
      isShow.value = false;
    }
    triggerInputText.value = localValue.value[currentIndex.value]?.join?.('-') || '';
    mode.value = EMode.edit;
    handleValueChange();
  }, 100);

  /**
   * 点击确认
   */
  const handleSubmit = _.debounce(() => {
    if (isClearAll.value) {
      return;
    }
    const allTime = _.cloneDeep(localValue.value);
    allTime.splice(currentIndex.value, 1);
    const isPass = timeRangeValidate(allTime, timeRange.value);
    if (isPass) {
      if (mode.value === EMode.edit) {
        isShow.value = false;
      }
      localValue.value[currentIndex.value] = [...timeRange.value];
      handleValueChange();
      // if (mode.value === EMode.add && props.allowNextFocus) {
      //   handleAddTimeRange();
      // }
    } else {
      if (mode.value === EMode.add) {
        localValue.value.splice(localValue.value.length - 1, 1);
      }
      messageWarn(t('时间段重叠了'));
    }
  }, 100);

  const handleClearAll = () => {
    localValue.value = [];
    isClearAll.value = true;
    handleValueChange();
  };

  // const handleSortTimeRange = (): Array<TimeRange> => {
  //   return localValue.value.sort((a, b) => {
  //     const time1 = +dayjs.tz(dayjs.tz().startOf('day').format(`YYYY-MM-DD ${a[0]}`)).format('x');
  //     const time2 = +dayjs.tz(dayjs.tz().startOf('day').format(`YYYY-MM-DD ${b[0]}`)).format('x');
  //     return time1 - time2;
  //   });
  // };

  const handleValueChange = () => {
    // if (props.autoSort) {
    //   localValue.value = handleSortTimeRange();
    // }
    const value = _.cloneDeep(localValue.value);
    modelValue.value = value;
    emit('change', value);
  };

  /**
   * 更新输入框的位置
   * @param insert 是否直接插入列表 新增时使用
   */
  const handleMoveTrigger = (insert = false) => {
    if (insert) {
      timeRangeListRef.value?.appendChild(triggerInputRef.value!);
    } else {
      targetEl.value?.append(triggerInputRef.value!);
    }
    nextTick(() => {
      triggerInputText.value = timeRange.value?.map?.((item) => handleFormatTime(item))?.join('-');
      timePickerRef.value?.$refs?.drop?.update?.();
      inputFocus();
    });
  };

  /**
   * 格式化时间
   * @param time 'HH:mm:ss'的顺序
   */
  const handleFormatTime = (time: string) => {
    if (!time) {
      return '';
    }
    const timeList = time.split(':');
    const formatList = ['HH', 'mm', 'ss'];
    const timeMap = timeList.reduce<Record<string, string>>((obj, time, index) => {
      const key = formatList[index];
      if (props.format.indexOf(key) > -1) {
        Object.assign(obj, { [key]: time });
      }
      return obj;
    }, {});
    return props.format.replace(TIME_FORMAT_REG, (word: string) => timeMap[word] || '');
  };

  /**
   * 解析自定义输入的时间范围
   * @param timeRagneStr 字符串 00:00-23:59
   * @returns TimeRange
   */
  const parseTimeRangeStr = (timeRagneStr: string): TimeRange | null => {
    try {
      const timeRange = timeRagneStr.split('-');
      const startTime = timeRange[0];
      const endTime = timeRange[1];
      const fn = (timeStr: string, index: number): string => {
        const time = timeStr.split(':');
        const [hour = '00', min = '00', sec = index ? '59' : '00'] = time;
        const timeList = [hour, min, sec];
        return timeList.reduce((total, cur, index) => {
          const reg = index ? /^\d$|^[0-5]\d$/ : /^\d$|^[0-1]\d$|^[2][0-4]$/;
          if (!reg.test(cur)) throw Error('时间格式错误');
          return total.concat(`${cur.padStart(2, '0')}${index !== timeList.length - 1 ? ':' : ''}`);
        }, '');
      };
      return [startTime, endTime].map(fn) as TimeRange;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  /**
   * 处理自定义输入时间的失焦时间
   * @returns void
   */
  const handleTimeRangeInputBlur = () => {
    isFocus.value = true;
    if (!isCustomTimeRange.value || !triggerInputText.value.length || !localValue.value.length) {
      isShow.value = false;
      return;
    }
    const customTimeRange = parseTimeRangeStr(triggerInputText.value);
    if (customTimeRange) {
      timeRange.value = customTimeRange;
      handleSubmit();
    } else {
      messageError(t('时间格式错误'));
    }
  };

  const handleTimeRangeInput = () => {
    isCustomTimeRange.value = true;
  };
</script>

<style lang="less">
  .time-picker-multiple-wrap {
    position: relative;
    display: flex;
    height: 24px;
    min-width: 240px;
    padding-right: 40px;
    cursor: pointer;
    border-bottom: 1px solid #c4c6cc;
    align-items: center;

    &:hover {
      .icon-mc-close-fill {
        display: initial;
      }
    }

    .icon-mc-time {
      margin-right: 8px;
      font-size: 16px;
      color: #c4c6cc;
    }

    .icon-mc-close-fill {
      position: absolute;
      top: 50%;
      right: 0;
      display: none;
      font-size: 14px;
      color: #c4c6cc;
      transform: translateY(-50%);

      &:hover {
        color: #979ba5;
      }
    }

    .placeholder {
      color: #c4c6cc;
    }

    .time-range-list {
      display: flex;
      align-items: center;
      height: 100%;

      .time-range-item {
        position: relative;
        display: flex;
        line-height: 20px;
        align-items: center;

        &::after {
          position: absolute;
          right: -6px;
          bottom: 1px;
          content: ',';
        }

        &:not(:first-child) {
          margin-left: 8px;
        }

        &.no-empty-time {
          &::after {
            display: none;
          }
        }
      }
    }

    .trigger-input-wrap {
      // height: 20px;

      &.hide-second {
        .trigger-input {
          width: 68px;
        }
      }

      .bk-date-picker {
        width: initial;
      }

      .trigger-input {
        width: 100px;
        height: 20px;
        padding: 0;
        border: 0;
        outline: none;
      }
    }
  }

  .time-range-multiple-popover {
    top: 24px !important;
  }
</style>
