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
  <Component :is="component" />
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import Page1 from './pages/page1/Index.vue';
  import Page2 from './pages/page2/Index.vue';

  const route = useRoute();

  const comMap = {
    ticket: Page1,
    success: Page2,
  };

  const page = ref('');

  const component = computed(() => {
    if (comMap[page.value as keyof typeof comMap]) {
      return comMap[page.value as keyof typeof comMap];
    }
    return Page1;
  });

  watch(route, () => {
    page.value = route.params.page as string;
  }, {
    immediate: true,
  });
</script>
