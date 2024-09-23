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
  <span>{{ getCostTimeDisplay(costTime) }}</span>
</template>

<script setup lang="ts">
  import { getCostTimeDisplay } from '@utils';

  import { useIntervalFn } from '@vueuse/core';

  interface Props {
    value: number;
    isTiming: boolean;
    startTime: number;
  }

  const props = defineProps<Props>();

  const costTime = ref(0);
  // 计时
  const { resume, pause } = useIntervalFn(
    () => {
      costTime.value = Math.floor(Date.now() / 1000) - props.startTime;
    },
    1000,
    { immediate: false },
  );

  watch(
    () => props.value,
    (time) => {
      if (!props.isTiming) {
        costTime.value = time;
      }
    },
    { immediate: true },
  );

  watch(
    () => props.isTiming,
    () => {
      props.isTiming ? resume() : pause();
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    pause();
  });
</script>
