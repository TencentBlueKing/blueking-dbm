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
    class="dbm-date-picker-panel"
    :class="{ 'has-sidebar': shortcuts.length > 0 }"
    @mousedown.prevent>
    <div class="dbm-date-picker-panel-body">
      <template v-if="isTimeView">
        <div class="dbm-date-picker-time-header">{{ formatDate(dates[0], 'YYYY-MM-DD') }}</div>
        <TimeSpinner
          ref="timeSpinnerRef"
          :disabled-times="disabledTimes"
          :hours="dates[0]?.getHours()"
          :minutes="dates[0]?.getMinutes()"
          :seconds="dates[0]?.getSeconds()"
          :show-seconds="showSeconds"
          @change="handleTimeChange" />
      </template>
      <template v-else>
        <PanelHeader
          :panel-date="panelDate"
          :table="table"
          @shift="handleShift"
          @switch-table="handleSwitchTable" />
        <DateTable
          v-if="table === 'date'"
          :dates="dates"
          :disabled-date="disabledDate"
          :table-date="panelDate"
          @pick="handleTablePick" />
        <MonthYearTable
          v-else
          :check-disabled="table === selectionMode"
          :dates="dates"
          :disabled-date="disabledDate"
          :mode="table === 'year' ? 'year' : 'month'"
          :table-date="panelDate"
          @pick="handleTablePick" />
      </template>
      <Confirm
        v-if="confirm"
        :clearable="clearable"
        :is-time="isTimeView"
        :show-time="showTime"
        :time-disabled="!dates[0]"
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
    getDisabledTimes,
    getShortcutValue,
    initTime,
    type InternalValue,
    type PickOptions,
    type SelectionMode,
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

  interface Props {
    activeShortcutIndex: number;
    clearable: boolean;
    /** 是否展示底部确认栏，展示时选中日期后不自动收起 */
    confirm: boolean;
    dates: InternalValue;
    disabledDate?: DisabledDate;
    selectionMode: SelectionMode;
    shortcutClose: boolean;
    shortcuts: DatePickerShortcut[];
    showSeconds: boolean;
    showTime: boolean;
    startDate?: Date;
  }

  interface Emits {
    (e: 'pick', dates: InternalValue, options: PickOptions): void;
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

  const timeSpinnerRef = useTemplateRef('timeSpinnerRef');

  const getPanelDate = () => shiftMonth(props.startDate || props.dates[0] || new Date(), 0);

  const isTimeView = ref(false);
  const table = ref<TableType>(props.selectionMode);
  const panelDate = ref(getPanelDate());

  const disabledTimes = computed(() => getDisabledTimes(props.dates[0], props.disabledDate));

  // 选中值变化后面板跳到选中值所在月份
  watch(
    () => props.dates,
    () => {
      panelDate.value = getPanelDate();
    },
  );

  watch(
    () => props.selectionMode,
    (mode) => {
      table.value = mode;
    },
  );

  const handleShift = (months: number) => {
    panelDate.value = shiftMonth(panelDate.value, months);
  };

  const handleSwitchTable = (value: TableType) => {
    table.value = value;
  };

  // 当前表格就是最终选择粒度时直接选中，否则只是导航（年 → 月 → 日）
  const handleTablePick = (value: Date) => {
    if (table.value !== props.selectionMode) {
      panelDate.value = value;
      table.value = table.value === 'year' ? 'month' : props.selectionMode;
      return;
    }
    let date = value;
    if (props.selectionMode === 'year') {
      date = new Date(value.getFullYear(), 0, 1);
    } else if (props.selectionMode === 'month') {
      date = new Date(value.getFullYear(), value.getMonth(), 1);
    }
    emits('pick', [date], { type: props.selectionMode });
  };

  const handleTimeChange = (part: TimePart, value: number) => {
    const date = setTimePart(props.dates[0] || initTime(), part, value);
    emits('pick', [date], { keepOpen: true, type: 'time' });
  };

  const handleToggleTime = () => {
    isTimeView.value = !isTimeView.value;
    if (isTimeView.value) {
      nextTick(() => timeSpinnerRef.value?.updateScroll());
    }
  };

  const handleShortcutSelect = (shortcut: DatePickerShortcut, index: number) => {
    const value = getShortcutValue(shortcut);
    if (value) {
      emits('pick', [Array.isArray(value) ? value[0] : value], { shortcut, type: 'shortcut' });
    }
    shortcut.onClick?.(shortcut, index);
    if (props.shortcutClose) {
      emits('pick-success');
    }
  };

  defineExpose<Exposes>({
    reset() {
      isTimeView.value = false;
      table.value = props.selectionMode;
      panelDate.value = getPanelDate();
    },
  });
</script>
