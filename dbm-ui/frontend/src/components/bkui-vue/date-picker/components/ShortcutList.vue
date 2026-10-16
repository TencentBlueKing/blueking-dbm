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
  <div class="dbm-date-picker-shortcuts">
    <div
      v-for="(item, index) in shortcuts"
      :key="index"
      class="dbm-date-picker-shortcut"
      :class="{ 'is-active': index === activeIndex }"
      @click="emits('select', item, index)">
      {{ item.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { DatePickerShortcut } from '../common';

  interface Props {
    activeIndex: number;
    shortcuts: DatePickerShortcut[];
  }

  type Emits = (e: 'select', shortcut: DatePickerShortcut, index: number) => void;

  defineProps<Props>();

  const emits = defineEmits<Emits>();
</script>
