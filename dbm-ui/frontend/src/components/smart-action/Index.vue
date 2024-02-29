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
  <div ref="root">
    <slot />
    <div
      ref="placeholderRef"
      role="placeholder"
      :style="placeholderStyles">
      <Teleport
        v-if="showActionArea"
        :disabled="!isFixed"
        to="body">
        <div
          v-show="isPlaceholderShow"
          ref="actionRef"
          :class="dymaicClasses"
          role="action"
          :style="dymaicStyles">
          <div :style="actionContentstyles">
            <slot name="action" />
          </div>
        </div>
      </Teleport>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

  interface Props {
    offsetTarget?: () => Element | null;
    fill?: number;
    showActionArea?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    fill: 0,
    offsetTarget: () => null,
    showActionArea: true,
  });

  const placeholderRef = ref();
  const actionRef = ref();

  const isPlaceholderShow = ref(false);
  const isFixed = ref(false);
  const paddingLeft = ref(0);
  const offsetLeft = ref(0);

  const placeholderStyles = computed(() => ({
    height: isFixed.value ? '50px' : 'auto',
  }));
  const dymaicClasses = computed(() => (isFixed.value ? 'smart' : ''));
  const dymaicStyles = computed(() => ({
    'padding-left': isFixed.value ? `${paddingLeft.value}px` : '0',
  }));
  const actionContentstyles = computed(() => ({
    'padding-left': `${offsetLeft.value + props.fill}px`,
    flex: 1,
  }));

  /**
   * @desc action 内容区相对 offsetTarget 的偏移位置
   */
  const calcOffsetLeft = _.debounce(() => {
    const $offsetTargetEl = props.offsetTarget();
    if (!$offsetTargetEl || !placeholderRef.value) {
      return;
    }

    const placeholderLeft = placeholderRef.value.getBoundingClientRect().left;
    const offsetTargetLeft = $offsetTargetEl.getBoundingClientRect().left;
    offsetLeft.value = offsetTargetLeft - placeholderLeft;
  }, 50);

  /**
   * @desc 当 placeholder 块是 fixed 效果时，修正左边位置的 paddingLeft
   */
  const smartPosition = _.throttle(() => {
    if (!placeholderRef.value) {
      return;
    }
    const { height, top, left } = placeholderRef.value.getBoundingClientRect();
    isFixed.value = height + top + 25 > window.innerHeight;
    paddingLeft.value = left;
    setTimeout(() => {
      isPlaceholderShow.value = true;
    });
  }, 300);

  onMounted(() => {
    window.addEventListener('resize', smartPosition);
    const observer = new MutationObserver(() => {
      calcOffsetLeft();
      smartPosition();
    });
    observer.observe(document.querySelector('body') as Node, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
    });
    calcOffsetLeft();
    smartPosition();
    onBeforeUnmount(() => {
      observer.takeRecords();
      observer.disconnect();
      window.removeEventListener('resize', smartPosition);
    });
  });
</script>
<style lang="less" scoped>
  .smart {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 99;
    display: flex;
    height: 52px;
    background: #fff;
    border-top: 1px solid #c4c6cc;
    box-shadow: 0 -2px 4px 0 rgb(0 0 0 / 6%);
    align-items: center;
  }
</style>
