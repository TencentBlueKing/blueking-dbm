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
    ref="rootRef"
    class="db-skeleton-loading">
    <component
      :is="renderCom"
      v-if="realLoading && maxWidth"
      class="skeleton-loading-mask"
      :class="{
        fullscreen
      }"
      :max-width="maxWidth"
      primary-color="#EBECF3"
      secondary-color="#F6F7FB"
      :speed="2" />
    <div :class="{ 'skeleton-loading-hidden': realLoading }">
      <slot />
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    onMounted,
    ref,
    watch,
  } from 'vue';

  import ClusterList from './components/ClusterList.vue';

  interface Props {
    name: string;
    loading: boolean;
    once?: boolean;
    fullscreen?:boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    loading: true,
    once: true,
    fullscreen: false,
  });

  const comMap = {
    clusterList: ClusterList,
  };

  const rootRef = ref();
  const maxWidth = ref(0);
  const realLoading = ref(true);

  const renderCom = comMap[props.name as keyof typeof comMap];

  const unwatch = watch(() => props.loading, (loading: boolean) => {
    if (loading) {
      realLoading.value = loading;
      return;
    }
    setTimeout(() => {
      realLoading.value = loading;
      if (!loading && props.once) {
        unwatch();
      }
    }, 1000);
  }, {
    immediate: true,
  });

  onMounted(() => {
    const { width } = rootRef.value.getBoundingClientRect();
    maxWidth.value = width;
  });
</script>
<style lang="less">
  .db-skeleton-loading {
    position: relative;

    .skeleton-loading-mask {
      position: absolute;
      inset: 0;
      z-index: 1;
      width: 100%;
      overflow: hidden;
      background: #f5f7fa;
      opacity: 100%;
      visibility: visible;

      &.fullscreen {
        min-height: calc(100vh - 92px);
      }
    }

    .skeleton-loading-hidden {
      opacity: 0%;
      visibility: hidden;
    }
  }
</style>
