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
  <div class="db-minimap">
    <div
      class="db-minimap__wrapper"
      :style="{
        width: width + 'px',
        height: height + 'px',
      }">
      <img :src="imgSrc" />
    </div>
    <div
      ref="viewportRef"
      class="db-minimap__viewport"
      :style="{
        width: viewportWidth + 'px',
        height: viewportHeight + 'px',
      }"
      @mousedown="handleMouseDown" />
  </div>
</template>

<script setup lang="ts">
  import { toPng } from 'html-to-image';
  import type { Options } from 'html-to-image/lib/types';
  import _ from 'lodash';

  interface Props {
    viewportWidth?: number;
    viewportHeight?: number;
    width?: number;
    height?: number;
  }

  interface Emits {
    (e: 'change', value: { left: number; top: number }): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    width: 380,
    height: 160,
    viewportWidth: 210,
    viewportHeight: 110,
  });
  const emits = defineEmits<Emits>();

  const imgSrc = ref('');
  const viewportRef = ref<HTMLDivElement>();

  function moveViewport(left: number, top: number) {
    if (!viewportRef.value) {
      return;
    }

    viewportRef.value.style.left = `${left}px`;
    viewportRef.value.style.top = `${top}px`;
  }

  function handleMouseDown(mouseDownEvent: MouseEvent) {
    mouseDownEvent.stopPropagation();
    mouseDownEvent.preventDefault();

    if (!viewportRef.value) {
      return;
    }

    const { offsetLeft, offsetTop } = viewportRef.value;
    // 获取 x 坐标和 y 坐标
    const { clientX, clientY } = mouseDownEvent;
    const startX = clientX - offsetLeft;
    const startY = clientY - offsetTop;

    const onMousemove = (e: MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      // 获取 x 坐标和 y 坐标
      const { clientX: endX, clientY: endY } = e;

      if (startX === endX && startY === endY) {
        return;
      }
      // 计算移动后的左偏移量和顶部的偏移量
      let left = endX - startX;
      let top = endY - startY;

      if (left < 0) {
        left = 0;
      }
      if (top < 0) {
        top = 0;
      }
      if (left + props.viewportWidth > props.width) {
        left = props.width - props.viewportWidth;
      }
      if (top + props.viewportHeight > props.height) {
        top = props.height - props.viewportHeight;
      }

      moveViewport(left, top);
      emits('change', { left, top });
    };
    const throttleMousemove = _.throttle(onMousemove, 50);
    document.body.addEventListener('mousemove', throttleMousemove);
    document.body.addEventListener('mouseup', () => {
      document.body.removeEventListener('mousemove', throttleMousemove);
    });
  }

  /**
   * 更新 canvas 绘制内容
   */
  function updateCanvas(el: HTMLElement, options: Options) {
    if (!el) {
      return;
    }

    toPng(el, options).then((url: string) => {
      imgSrc.value = url;
    });
  }

  defineExpose({
    updateCanvas,
  });
</script>

<style lang="less" scoped>
  .db-minimap {
    position: relative;
    overflow: hidden;

    &__wrapper {
      position: relative;
      user-select: none;

      > img {
        width: 100%;
      }

      &::before {
        position: absolute;
        inset: 0;
        content: '';
      }
    }

    &__viewport {
      position: absolute;
      top: 0;
      left: 0;
      z-index: 10;
      cursor: move;
      border: 1px solid #3a84ff;
    }
  }
</style>
