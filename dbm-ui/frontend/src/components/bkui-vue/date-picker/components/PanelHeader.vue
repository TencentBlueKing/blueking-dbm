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
  <div class="dbm-date-picker-panel-header">
    <span
      class="dbm-date-picker-panel-header-btn is-prev"
      @click="handleShift(-1, true)">
      <AngleDoubleLeft />
    </span>
    <span
      v-if="table === 'date'"
      class="dbm-date-picker-panel-header-btn is-prev"
      @click="handleShift(-1, false)">
      <AngleLeft />
    </span>
    <span
      class="dbm-date-picker-panel-header-btn is-next"
      @click="handleShift(1, true)">
      <AngleDoubleRight />
    </span>
    <span
      v-if="table === 'date'"
      class="dbm-date-picker-panel-header-btn is-next"
      @click="handleShift(1, false)">
      <AngleRight />
    </span>
    <span v-if="table === 'year'">{{ decadeStart }} - {{ decadeStart + 9 }}</span>
    <template v-else>
      <span
        class="dbm-date-picker-panel-header-label"
        @click="emits('switch-table', 'year')">
        {{ panelDate.getFullYear() }}
      </span>
      <template v-if="table === 'date'">
        -
        <span
          class="dbm-date-picker-panel-header-label"
          @click="emits('switch-table', 'month')">
          {{ String(panelDate.getMonth() + 1).padStart(2, '0') }}
        </span>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { AngleDoubleLeft, AngleDoubleRight, AngleLeft, AngleRight } from 'bkui-vue/lib/icon';

  import type { TableType } from '../common';

  interface Props {
    panelDate: Date;
    table: TableType;
  }

  interface Emits {
    /** 面板日期偏移的月数 */
    (e: 'shift', months: number): void;
    (e: 'switch-table', table: TableType): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const decadeStart = computed(() => Math.floor(props.panelDate.getFullYear() / 10) * 10);

  // 双箭头：年视图翻 10 年，其余翻 1 年；单箭头只在日期视图出现，翻 1 个月
  const handleShift = (direction: 1 | -1, isDouble: boolean) => {
    if (!isDouble) {
      emits('shift', direction);
      return;
    }
    emits('shift', direction * (props.table === 'year' ? 120 : 12));
  };
</script>
