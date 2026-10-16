<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    class="dbm-date-picker-panel is-range"
    :class="{ 'has-sidebar': shortcuts.length > 0 }"
    @mousedown.prevent>
    <div class="dbm-date-picker-panel-body">
      <div
        v-if="isTimeView"
        class="dbm-date-picker-range-content">
        <div
          v-for="(side, index) in TIME_SIDES"
          :key="side"
          class="dbm-date-picker-range-item">
          <div class="dbm-date-picker-time-header">{{ formatDate(localDates[index], 'YYYY-MM-DD') }}</div>
          <TimeSpinner
            ref="timeSpinnerRefs"
            :disabled-times="getDisabledTimes(localDates[index], disabledDate)"
            :hours="localDates[index]?.getHours()"
            :minutes="localDates[index]?.getMinutes()"
            :seconds="localDates[index]?.getSeconds()"
            :show-seconds="showSeconds"
            @change="(part: TimePart, value: number) => handleTimeChange(side, part, value)" />
        </div>
      </div>
      <div
        v-else
        class="dbm-date-picker-range-content">
        <div
          v-for="position in PANEL_POSITIONS"
          :key="position"
          class="dbm-date-picker-range-item">
          <PanelHeader
            :panel-date="panels[position].date"
            :table="panels[position].table"
            @shift="(months: number) => handleShift(position, months)"
            @switch-table="(value: TableType) => (panels[position].table = value)" />
          <DateTable
            v-if="panels[position].table === 'date'"
            :dates="localDates"
            :disabled-date="disabledDate"
            :range-state="rangeState"
            :table-date="panels[position].date"
            @pick="handleRangePick"
            @range-change="handleRangeChange" />
          <MonthYearTable
            v-else
            :dates="localDates"
            :mode="panels[position].table === 'year' ? 'year' : 'month'"
            :table-date="panels[position].date"
            @pick="(value: Date) => handlePreSelection(position, value)" />
        </div>
      </div>
      <Confirm
        v-if="confirm"
        :clearable="clearable"
        :is-time="isTimeView"
        :show-time="showTime"
        :time-disabled="!(localDates[0] && localDates[1])"
        @clear="emits('pick-clear')"
        @confirm="emits('pick-success')"
        @toggle-time="handleToggleTime" />
    </div>
    <ShortcutList
      v-if="shortcuts.length"
      :active-index="activeShortcutIndex"
      :shortcuts="shortcuts"
      @select="handleShortcutSelect" />
  </div>
</template>

<script setup lang="ts">
  import {
    type DatePickerShortcut,
    type DisabledDate,
    formatDate,
    getDayEnd,
    getDisabledTimes,
    getMonthIndex,
    getShortcutValue,
    type InternalValue,
    type PickOptions,
    type RangeState,
    setTimePart,
    shiftMonth,
    type TableType,
    type TimePart,
  } from '../common';

  import Confirm from './Confirm.vue';
  import DateTable from './DateTable.vue';
  import MonthYearTable from './MonthYearTable.vue';
  import PanelHeader from './PanelHeader.vue';
  import ShortcutList from './ShortcutList.vue';
  import TimeSpinner from './TimeSpinner.vue';

  type PanelPosition = 'left' | 'right';

  interface Props {
    activeShortcutIndex: number;
    clearable: boolean;
    /** 是否展示底部确认栏，展示时选完起止日期后不自动收起 */
    confirm: boolean;
    dates: InternalValue;
    disabledDate?: DisabledDate;
    shortcutClose: boolean;
    shortcuts: DatePickerShortcut[];
    showSeconds: boolean;
    showTime: boolean;
    startDate?: Date;
  }

  interface Emits {
    (e: 'pick', dates: InternalValue, options: PickOptions): void;
    (e: 'pick-first', date: Date): void;
    (e: 'pick-clear' | 'pick-success'): void;
  }

  interface Exposes {
    reset: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabledDate: undefined,
    startDate: undefined,
  });

  const emits = defineEmits<Emits>();

  const PANEL_POSITIONS: PanelPosition[] = ['left', 'right'];
  const TIME_SIDES = ['start', 'end'] as const;

  const timeSpinnerRefs = ref<InstanceType<typeof TimeSpinner>[]>([]);

  const sortDates = (dates: InternalValue) =>
    [...dates].sort((a, b) => (a && b ? a.getTime() - b.getTime() : 0)) as InternalValue;

  const isTimeView = ref(false);
  const localDates = ref<InternalValue>(sortDates(props.dates));
  const rangeState = reactive<RangeState>({
    from: localDates.value[0],
    selecting: false,
    to: localDates.value[1],
  });
  const panels = reactive<Record<PanelPosition, { date: Date; table: TableType }>>({
    left: { date: new Date(), table: 'date' },
    right: { date: new Date(), table: 'date' },
  });

  // 左侧展示起始月，右侧默认下一个月；结束日期更靠后时右侧直接展示结束月
  const setPanelDates = () => {
    const leftDate = shiftMonth(props.startDate || localDates.value[0] || new Date(), 0);
    let rightDate = shiftMonth(leftDate, 1);
    const endDate = localDates.value[1];
    if (endDate && getMonthIndex(endDate) > getMonthIndex(rightDate)) {
      rightDate = shiftMonth(endDate, 0);
    }
    panels.left.date = leftDate;
    panels.right.date = rightDate;
  };

  setPanelDates();

  const syncFromProps = () => {
    localDates.value = sortDates(props.dates);
    Object.assign(rangeState, { from: localDates.value[0], selecting: false, to: localDates.value[1] });
    setPanelDates();
  };

  watch(() => props.dates, syncFromProps);

  // 左右面板翻页互相约束：始终保持左侧月份早于右侧
  const handleShift = (position: PanelPosition, months: number) => {
    panels[position].date = shiftMonth(panels[position].date, months);
    if (getMonthIndex(panels.left.date) < getMonthIndex(panels.right.date)) {
      return;
    }
    if (position === 'left') {
      panels.right.date = shiftMonth(panels.left.date, 1);
    } else {
      panels.left.date = shiftMonth(panels.right.date, -1);
    }
  };

  // 年、月表格只做导航：年 → 月 → 日
  const handlePreSelection = (position: PanelPosition, value: Date) => {
    const panel = panels[position];
    panel.table = panel.table === 'year' ? 'month' : 'date';
    handleShift(position, getMonthIndex(value) - getMonthIndex(panel.date));
  };

  // 第一次点击记为起点，第二次点击完成选择；结束日期取当天 23:59:59
  const handleRangePick = (value: Date) => {
    if (!rangeState.selecting) {
      emits('pick-first', value);
      Object.assign(rangeState, { from: value, selecting: true, to: null });
      return;
    }
    const [start, end] = [rangeState.from || value, value].sort((a, b) => a.getTime() - b.getTime());
    const dates = [new Date(start), getDayEnd(end)];
    localDates.value = dates;
    Object.assign(rangeState, { from: dates[0], selecting: false, to: dates[1] });
    emits('pick', dates, { type: 'date' });
  };

  const handleRangeChange = (value: Date) => {
    rangeState.to = value;
  };

  // 结束时间早于开始时间时，以本次修改的一侧为准拉齐另一侧
  const handleTimeChange = (side: (typeof TIME_SIDES)[number], part: TimePart, value: number) => {
    let [start, end] = localDates.value.map((item) => new Date(item!));
    if (side === 'start') {
      start = setTimePart(start, part, value);
    } else {
      end = setTimePart(end, part, value);
    }
    if (end < start) {
      if (side === 'start') {
        end = new Date(start);
      } else {
        start = new Date(end);
      }
    }
    emits('pick', [start, end], { keepOpen: true, type: 'time' });
  };

  const handleToggleTime = () => {
    isTimeView.value = !isTimeView.value;
    if (isTimeView.value) {
      nextTick(() => timeSpinnerRefs.value?.forEach((item) => item?.updateScroll()));
    }
  };

  const handleShortcutSelect = (shortcut: DatePickerShortcut, index: number) => {
    // 与 bk-date-picker 一致：没有有效范围值的快捷项不响应（含 onClick）
    const value = getShortcutValue(shortcut);
    if (!Array.isArray(value) || value.length < 2) {
      return;
    }
    shortcut.onClick?.(shortcut, index);
    emits('pick', [new Date(value[0]), new Date(value[1])], { shortcut, type: 'shortcut' });
    if (props.shortcutClose) {
      emits('pick-success');
    }
  };

  defineExpose<Exposes>({
    reset() {
      isTimeView.value = false;
      panels.left.table = 'date';
      panels.right.table = 'date';
      syncFromProps();
    },
  });
</script>
