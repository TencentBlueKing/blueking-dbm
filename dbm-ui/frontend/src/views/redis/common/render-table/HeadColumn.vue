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
  <th
    :class="{
      'edit-required': required,
      [`column-${columnKey}`]: true
    }"
    :data-minWidth="minWidth"
    :style="styles"
    @mousedown="handleMouseDown"
    @mousemove="handleMouseMove">
    <div
      v-overflow-tips
      class="th-cell">
      <slot />
    </div>
    <div
      v-if="slots.append"
      style="display: inline-block; line-height: 40px; vertical-align: top;">
      <slot name="append" />
    </div>
  </th>
</template>
<script setup lang="ts">
  import {
    computed,
    inject,
    useSlots,
  } from 'vue';

  import { random } from '@utils';

  interface Props {
    width?: number;
    required?: boolean;
    minWidth?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    width: undefined,
    required: true,
    minWidth: undefined,
  });

  const slots = useSlots();

  const columnKey  = random();

  const parentTable = inject('mysqlToolRenderTable', {} as any);

  const styles = computed(() => ({
    width: props.width ? `${props.width}px` : '',
  }));

  const handleMouseDown = (event: MouseEvent) => {
    parentTable?.columnMousedown(event, {
      columnKey,
      minWidth: props.minWidth,
    });
  };

  const handleMouseMove = (event: MouseEvent) => {
    parentTable?.columnMouseMove(event);
  };

</script>
