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
  <Component :is="com" />
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import Step1 from './steps/step1/Index.vue';
  import Step2 from './steps/step2/Index.vue';

  const route = useRoute();

  const comMap = {
    execute: Step1,
    success: Step2,
  };

  const step = ref('');

  const com = computed(() => {
    if (comMap[step.value as keyof typeof comMap]) {
      return comMap[step.value as keyof typeof comMap];
    }
    return Step1;
  });

  watch(route, () => {
    step.value = route.params.step as string;
  }, {
    immediate: true,
  });
</script>
