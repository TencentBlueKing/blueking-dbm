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
  <div class="dbm-date-picker-time">
    <div class="dbm-date-picker-time-titles">
      <div
        v-for="column in columns"
        :key="column.part"
        class="dbm-date-picker-time-title">
        {{ column.title }}
      </div>
    </div>
    <div class="dbm-date-picker-time-body">
      <!-- 选中行高亮条，选中项始终滚动到列表顶部 -->
      <div class="dbm-date-picker-time-highlight" />
      <div
        v-for="column in columns"
        :key="column.part"
        :ref="(el) => setListRef(column.part, el as HTMLElement | null)"
        class="dbm-date-picker-time-list"
        @scroll="scrollHandlers[column.part]">
        <ul>
          <li
            v-for="item in column.max"
            :key="item"
            class="dbm-date-picker-time-cell"
            :class="{
              'is-disabled': column.disabled.includes(item - 1),
              'is-selected': column.value === item - 1,
            }"
            @click="handleClick(column.part, item - 1)">
            {{ String(item - 1).padStart(2, '0') }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { TimePart } from '../common';

  interface Props {
    disabledTimes?: Record<TimePart, number[]>;
    hours?: number;
    minutes?: number;
    seconds?: number;
    showSeconds?: boolean;
  }

  type Emits = (e: 'change', part: TimePart, value: number) => void;

  interface Exposes {
    updateScroll: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabledTimes: () => ({ hours: [], minutes: [], seconds: [] }),
    hours: undefined,
    minutes: undefined,
    seconds: undefined,
    showSeconds: true,
  });

  const emits = defineEmits<Emits>();

  // 与样式中的单行高度保持一致
  const ITEM_HEIGHT = 32;

  const { t } = useI18n();

  const listRefs: Partial<Record<TimePart, HTMLElement>> = {};

  const columns = computed(() => {
    const list = [
      { disabled: props.disabledTimes.hours, max: 24, part: 'hours' as const, title: t('时'), value: props.hours },
      {
        disabled: props.disabledTimes.minutes,
        max: 60,
        part: 'minutes' as const,
        title: t('分'),
        value: props.minutes,
      },
      {
        disabled: props.disabledTimes.seconds,
        max: 60,
        part: 'seconds' as const,
        title: t('秒'),
        value: props.seconds,
      },
    ];
    return props.showSeconds ? list : list.slice(0, 2);
  });

  const setListRef = (part: TimePart, el: HTMLElement | null) => {
    if (el) {
      listRefs[part] = el;
    } else {
      delete listRefs[part];
    }
  };

  const scrollToValue = (part: TimePart, value: number | undefined, behavior: ScrollBehavior = 'smooth') => {
    const el = listRefs[part];
    if (!el || value === undefined) {
      return;
    }
    el.scrollTo({ behavior, top: value * ITEM_HEIGHT });
  };

  const handleClick = (part: TimePart, value: number) => {
    if (props.disabledTimes[part].includes(value)) {
      return;
    }
    emits('change', part, value);
  };

  // 滚轮滚动停止后，取停在高亮条位置的值；不可选时滚回当前值
  const createScrollHandler = (part: TimePart) =>
    debounce(() => {
      const el = listRefs[part];
      if (!el) {
        return;
      }
      const value = Math.round(el.scrollTop / ITEM_HEIGHT);
      if (value === props[part]) {
        return;
      }
      if (props.disabledTimes[part].includes(value)) {
        scrollToValue(part, props[part]);
        return;
      }
      emits('change', part, value);
    }, 200);

  const scrollHandlers: Record<TimePart, () => void> = {
    hours: createScrollHandler('hours'),
    minutes: createScrollHandler('minutes'),
    seconds: createScrollHandler('seconds'),
  };

  const updateScroll = () => {
    nextTick(() => {
      columns.value.forEach((column) => scrollToValue(column.part, column.value, 'auto'));
    });
  };

  watch(
    () => props.hours,
    (value) => scrollToValue('hours', value),
  );

  watch(
    () => props.minutes,
    (value) => scrollToValue('minutes', value),
  );

  watch(
    () => props.seconds,
    (value) => scrollToValue('seconds', value),
  );

  onMounted(updateScroll);

  defineExpose<Exposes>({
    updateScroll,
  });
</script>
