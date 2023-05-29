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
    ref="wrapperRef"
    class="stretch-layout-resize"
    @mousedown="handleMouseDown">
    <div class="resize-box">
      <div class="drag-line" />
      <div class="drag-flag">
        <template
          v-for="i in rounds"
          :key="i">
          <div
            class="move-round"
            :class="{ 'move-square': i === 3 }" />
        </template>
      </div>
    </div>
    <div
      v-if="showTrigger"
      class="resize-trigger">
      <span
        class="resize-trigger-button resize-trigger-left"
        @click="handleDirection('left')">
        <DbIcon
          style="display: inline-block; transform: rotate(180deg)"
          type="right-big" />
      </span>
      <span
        class="resize-trigger-button resize-trigger-right"
        @click="handleDirection('right')">
        <DbIcon type="right-big" />
      </span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { onMounted, ref } from 'vue';

  interface Props {
    showTrigger: boolean;
  }

  withDefaults(defineProps<Props>(), {
    showTrigger: true,
  });

  const emits = defineEmits<{
    trigger: [isLeft: boolean];
    change: [leftWidth: number];
    open: [direction: string];
  }>();

  const rounds = [1, 2, 3, 4, 5];
  const wrapperRef = ref<HTMLDivElement>();
  const isMoving = ref(false);

  const handleMouseDown = (event: MouseEvent) => {
    if (event.button !== 0) {
      return;
    }
    isMoving.value = true;
    const target = (wrapperRef.value as HTMLElement).parentElement as HTMLElement;

    document.onselectstart = () => false;
    document.ondragstart = () => false;

    const handleMouseMove = (event: MouseEvent) => {
      document.body.style.cursor = 'col-resize';
      const rect = target.getBoundingClientRect();
      emits('change', event.clientX - rect.left);
    };

    const handleMouseUp = () => {
      isMoving.value = false;
      document.body.style.cursor = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.onselectstart = null;
      document.ondragstart = null;
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleDirection = (direction: string) => {
    emits('open', direction);
  };

  onMounted(() => {
    const parentElment = wrapperRef.value?.parentElement;
    if (parentElment) {
      parentElment.style.position = 'relative';
    }
  });
</script>
<style lang="less" scoped>
  .stretch-layout-resize {
    position: absolute;
    top: 0;
    bottom: 0;
    z-index: 999;
    margin-left: 1px;

    .resize-box {
      position: absolute;
      top: 0;
      bottom: 0;
      left: -4px;
      display: flex;
      padding: 0 3px;
      cursor: col-resize;
      align-items: center;

      .drag-line {
        display: flex;
        width: 3px;
        height: 100%;
        padding: 1px;

        &::after {
          width: 1px;
          background: #eaebf0;
          content: '';
        }

        &:hover {
          z-index: 1;
          background: #3a84ff;
          transition: all 0.1s;

          &::after {
            background: transparent;
          }
        }
      }

      .drag-flag {
        position: absolute;
        margin-left: -3px;

        .move-round {
          width: 2px;
          height: 2px;
          margin-bottom: 3px;
          background-color: #63656e;
          border-radius: 50%;

          &.move-square {
            width: 2px;
            height: 2px;
            border-radius: 0%;
            transform: rotate(45deg);
            transform-origin: center;
          }
        }
      }
    }

    .resize-trigger {
      position: absolute;
      top: 8px;
      right: -16px;
      display: flex;
      align-items: center;

      .resize-trigger-button {
        display: flex;
        width: 16px;
        height: 28px;
        font-size: 12px;
        line-height: 28px;
        color: #699df4;
        cursor: pointer;
        background-color: #fafbfd;
        border: 1px solid #699df4;
        justify-content: center;
        align-items: center;

        &.resize-trigger-left {
          margin-right: -1px;
          border-radius: 4px 0 0 4px;
        }

        &.resize-trigger-right {
          border-radius: 0 4px 4px 0;
        }

        &:hover {
          color: white;
          background-color: #3a84ff;
          border-color: #3a84ff;
        }
      }
    }
  }
</style>
