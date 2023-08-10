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
      [`column-${columnKey}`]: true,
      'shadow-left': isFixed
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
    type StyleValue,
    useSlots  } from 'vue';

  import { random } from '@utils';

  interface Props {
    width?: number;
    required?: boolean;
    minWidth?: number;
    isFixed?: boolean;
    rowWidth?: number;
    isMinimum?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    width: undefined,
    required: true,
    minWidth: undefined,
    isFixed: false,
    rowWidth: 0,
    isMinimum: false,
  });

  const slots = useSlots();

  const columnKey  = random();

  const parentTable = inject('mysqlToolRenderTable', {} as any);

  let initWidthRate = 0;

  watch(() => [props.width, props.rowWidth], ([width, rowWidth]) => {
    if (props.width && props.rowWidth && props.minWidth) {
      if (width && rowWidth && initWidthRate === 0) {
        initWidthRate = props.isMinimum ?  props.minWidth / rowWidth : width / rowWidth;
      }
    }
  }, {
    immediate: true,
  });


  const styles = computed<StyleValue>(() => {
    if (props.width && props.rowWidth && props.minWidth) {
      const newWidth = props.rowWidth * initWidthRate;
      if (newWidth !== props.width) {
        // 宽度变化了
        const width = newWidth > props.minWidth ? newWidth : props.minWidth;
        return {
          width: `${width}px`,
          position: props.isFixed ? 'sticky' : 'relative',
          right: props.isFixed ? 0 : '',
        };
      }
    }
    return {
      width: props.width ? `${props.width}px` : '',
      position: props.isFixed ? 'sticky' : 'relative',
      right: props.isFixed ? 0 : '',
    };
  });

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
