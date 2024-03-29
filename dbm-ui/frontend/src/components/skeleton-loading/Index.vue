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
  <div ref="rootRef">
    <div
      v-if="name && loading"
      class="db-skeleton-loading">
      <Component
        :is="renderCom"
        class="skeleton-loading-mask"
        :max-width="maxWidth"
        primary-color="#EBECF3"
        secondary-color="#F6F7FB"
        :speed="2" />
      <div :class="{ 'skeleton-loading-hidden': loading }">
        <slot />
      </div>
    </div>
    <slot v-else />
  </div>
</template>
<script setup lang="ts">
  import { onMounted, ref } from 'vue';

  import ClusterList from './components/ClusterList.vue';

  interface Props {
    name?: string;
    loading: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    name: undefined,
    loading: true,
  });

  const comMap = {
    clusterList: ClusterList,
  };

  const rootRef = ref();
  const maxWidth = ref(0);

  const renderCom = computed(() => (props.name ? comMap[props.name as keyof typeof comMap] : 'div'));

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
    }

    .skeleton-loading-hidden {
      opacity: 0%;
      visibility: hidden;
    }
  }
</style>
