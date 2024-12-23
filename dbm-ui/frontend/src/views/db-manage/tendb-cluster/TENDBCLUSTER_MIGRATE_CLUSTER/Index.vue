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
  <Component :is="components[page]" />
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import Page2 from '@views/db-manage/common/create-ticket-success/Index.vue';

  import Page1 from './Create.vue';

  const route = useRoute();

  const components = {
    create: Page1,
    success: Page2,
  };

  const page = computed(() => (route.params.page as keyof typeof components) || 'create');
</script>
