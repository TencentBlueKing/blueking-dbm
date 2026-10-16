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
  <div class="dbm-date-picker-period-table">
    <span
      v-for="cell in cells"
      :key="cell.time"
      class="dbm-date-picker-cell"
      :class="{
        'is-disabled': cell.disabled,
        'is-selected': cell.selected,
        'is-today': cell.current,
      }"
      @click="handleClick(cell)">
      <em>{{ cell.text }}</em>
    </span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type DisabledDate, getMonthLabels, type InternalValue } from '../common';

  interface Props {
    /** 是否按 disabledDate 禁用：仅当月/年就是最终选择粒度时生效，作为日期导航时不禁用 */
    checkDisabled?: boolean;
    dates: InternalValue;
    disabledDate?: DisabledDate;
    mode: 'month' | 'year';
    tableDate: Date;
  }

  type Emits = (e: 'pick', value: Date) => void;

  interface Cell {
    current: boolean;
    date: Date;
    disabled: boolean;
    selected: boolean;
    text: number | string;
    time: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    checkDisabled: false,
    disabledDate: undefined,
  });

  const emits = defineEmits<Emits>();

  const { locale } = useI18n();

  const monthLabels = computed(() => getMonthLabels(locale.value));

  // 年视图每页 10 年，月视图固定 12 个月
  const cells = computed<Cell[]>(() => {
    const year = props.tableDate.getFullYear();
    const month = props.tableDate.getMonth();
    const now = new Date();
    const validDates = props.dates.filter((item): item is Date => !!item);

    if (props.mode === 'year') {
      const startYear = Math.floor(year / 10) * 10;
      return Array.from({ length: 10 }, (_, index) => {
        const cellYear = startYear + index;
        // 年视图作为导航时保留面板当前月份
        const date = new Date(cellYear, month, 1);
        return {
          current: cellYear === now.getFullYear(),
          date,
          disabled: props.checkDisabled && !!props.disabledDate?.(new Date(cellYear, 0, 1)),
          selected: validDates.some((item) => item.getFullYear() === cellYear),
          text: cellYear,
          time: date.getTime(),
        };
      });
    }

    return monthLabels.value.map((label, index) => {
      const date = new Date(year, index, 1);
      return {
        current: year === now.getFullYear() && index === now.getMonth(),
        date,
        disabled: props.checkDisabled && !!props.disabledDate?.(date),
        selected: validDates.some((item) => item.getFullYear() === year && item.getMonth() === index),
        text: label,
        time: date.getTime(),
      };
    });
  });

  const handleClick = (cell: Cell) => {
    if (cell.disabled) {
      return;
    }
    emits('pick', new Date(cell.date));
  };
</script>
