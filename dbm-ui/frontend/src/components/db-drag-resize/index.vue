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
    class="db-drag-resize"
    @mousedown="handleMouseDown">
    <div
      class="drag-wrapper">
      <span class="line-wrap">
        <span
          class="line"
          :class="{ 'is-moving': isMoving }">
          <div class="line-round-wrap">
            <template
              v-for="i in rounds"
              :key="i">
              <span
                class="line-round"
                :class="{ 'line-square': i === 3 }" />
            </template>
          </div>
        </span>
      </span>
    </div>
    <div
      v-if="showTrigger"
      class="resize-trigger">
      <span
        class="resize-trigger-button resize-trigger-left"
        @click="handleTrigger(true)">
        <DbIcon
          style="display: inline-block; transform:rotate(180deg)"
          type="right-big" />
      </span>
      <span
        class="resize-trigger-button resize-trigger-right"
        @click="handleTrigger(false)">
        <DbIcon type="right-big" />
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
  type MouseUp = () => void;

  interface Props {
    minWidth: number,
    maxWidth: number,
    showTrigger: boolean,
  }

  const props = withDefaults(defineProps<Props>(), {
    minWidth: 200,
    maxWidth: 500,
    showTrigger: true,
  });

  const emits = defineEmits<{
    move: [left: number, swipeRight: boolean, cancelFn: MouseUp],
    trigger: [isLeft: boolean]
  }>();

  const rounds = [1, 2, 3, 4, 5];
  const wrapperRef = ref<HTMLDivElement>();
  const isMoving = ref(false);

  const handleMouseDown = (mouseDownEvent: MouseEvent) => {
    const triggerWidth = 3;
    const target = wrapperRef.value?.parentElement;
    let mouseX = mouseDownEvent.clientX;

    document.onselectstart = () => false;
    document.ondragstart = () => false;

    const handleMouseMove = (event: MouseEvent) => {
      isMoving.value = true;
      const swipeRight = event.clientX - mouseX >= 0;
      mouseX = event.clientX;
      document.body.style.cursor = 'col-resize';
      if (target) {
        const rect = target.getBoundingClientRect();
        const isCollapse = (event.clientX - rect.left + triggerWidth) < props.minWidth;

        if (isCollapse) {
          emits('move', 0, swipeRight, handleMouseUp);
          handleMouseUp();
        } else {
          const curLeft = Math.min(
            Math.max(props.minWidth, event.clientX - rect.left),
            props.maxWidth,
          );
          emits('move', curLeft, swipeRight, handleMouseUp);
          if (curLeft >= props.maxWidth) {
            handleMouseUp();
          }
        }
      }
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

  const handleTrigger = (isLeft: boolean) => {
    emits('trigger', isLeft);
  };

  onMounted(() => {
    const parentElment = wrapperRef.value?.parentElement;
    if (parentElment) {
      parentElment.style.position = 'relative';
    }
  });
</script>

<style lang="less" scoped>
.db-drag-resize {
  .drag-wrapper {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 14;
    display: flex;
    width: 3px;

    .line-wrap {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 3px;

      &:hover {
        cursor: col-resize;

        .line {
          background-color: #3a84ff;

          .line-round {
            background-color: #3a84ff !important;
          }
        }
      }

      .line {
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        z-index: 2;
        display: flex;
        width: 2px;
        align-items: center;
        justify-content: center;

        &.is-moving {
          background-color: #3a84ff;

          .line-round {
            background-color: #3a84ff !important;
          }
        }

        .line-round-wrap {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          margin-left: -8px;
          pointer-events: none;

          .line-round {
            width: 2px;
            height: 2px;
            margin-bottom: 6px;
            background-color: #63656e;
            border-radius: 50%;

            &.line-square {
              width: 2px;
              height: 2px;
              border-radius: 0%;
              transform: rotate(45deg);
              transform-origin: center;
            }
          }
        }
      }
    }
  }

  .resize-trigger {
    position: absolute;
    top: 8px;
    right: -15px;
    z-index: 12;
    display: flex;
    align-items: center;

    .resize-trigger-button {
      display: flex;
      width: 16px;
      height: 28px;
      font-size: 12px;
      line-height: 28px;
      cursor: pointer;
      background-color: #fafbfd;
      border: 1px solid #dcdee5;
      justify-content: center;
      align-items: center;

      &.resize-trigger-left {
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
