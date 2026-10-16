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
  <div class="dbm-date-picker-date-table">
    <div class="dbm-date-picker-date-table-header">
      <span
        v-for="(day, index) in weekdays"
        :key="index">
        {{ day }}
      </span>
    </div>
    <span
      v-for="cell in cells"
      :key="cell.time"
      class="dbm-date-picker-cell"
      :class="{
        'is-disabled': cell.disabled,
        'is-other-month': !cell.inMonth,
        'is-range': cell.range,
        'is-selected': cell.selected,
        'is-today': cell.today,
      }"
      @click="handleClick(cell)"
      @mouseenter="handleMouseenter(cell)">
      <em>{{ cell.text }}</em>
    </span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { clearHours, type DisabledDate, getWeekdayLabels, type InternalValue, type RangeState } from '../common';

  interface Props {
    dates: InternalValue;
    disabledDate?: DisabledDate;
    /** 传入即为范围选择模式 */
    rangeState?: RangeState;
    tableDate: Date;
  }

  type Emits = (e: 'pick' | 'range-change', value: Date) => void;

  interface Cell {
    disabled: boolean;
    inMonth: boolean;
    range: boolean;
    selected: boolean;
    text: number;
    time: number;
    today: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabledDate: undefined,
    rangeState: undefined,
  });

  const emits = defineEmits<Emits>();

  const { locale } = useI18n();

  const weekdays = computed(() => getWeekdayLabels(locale.value));

  // 固定 6 行 42 格，从当月 1 号所在周的周日开始
  const cells = computed<Cell[]>(() => {
    const year = props.tableDate.getFullYear();
    const month = props.tableDate.getMonth();
    const startOffset = new Date(year, month, 1).getDay();
    const today = clearHours(new Date());
    const { rangeState } = props;
    // 范围选择进行中只高亮第一次点击的日期
    const activeDates = rangeState?.selecting ? [rangeState.from] : props.dates;
    const selectedTimes = activeDates.filter((item): item is Date => !!item).map(clearHours);
    const rangeTimes = [rangeState?.from, rangeState?.to]
      .filter((item): item is Date => !!item)
      .map(clearHours)
      .sort((a, b) => a - b);

    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(year, month, 1 - startOffset + index);
      const time = date.getTime();
      const inMonth = date.getMonth() === month;
      const selected = inMonth && selectedTimes.includes(time);
      return {
        disabled: !!props.disabledDate?.(new Date(time)),
        inMonth,
        range: inMonth && !selected && rangeTimes.length === 2 && time >= rangeTimes[0] && time <= rangeTimes[1],
        selected,
        text: date.getDate(),
        time,
        today: time === today,
      };
    });
  });

  const handleClick = (cell: Cell) => {
    if (cell.disabled) {
      return;
    }
    emits('pick', new Date(cell.time));
  };

  const handleMouseenter = (cell: Cell) => {
    if (!props.rangeState?.selecting || cell.disabled) {
      return;
    }
    emits('range-change', new Date(cell.time));
  };
</script>
