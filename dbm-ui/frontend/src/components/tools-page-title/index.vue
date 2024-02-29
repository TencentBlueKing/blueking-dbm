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
  <div class="toolbox-title-box">
    <span class="title">{{ toolboxTitle }}</span>
    <slot />
  </div>
</template>

<script setup lang="ts">
  import type { RouteRecordRaw } from 'vue-router';

  interface Props {
    toolboxRoutes: RouteRecordRaw[];
  }

  const props = defineProps<Props>();

  const route = useRoute();

  const toolboxTitle = ref('');

  const titleMap = computed(() =>
    props.toolboxRoutes.reduce(
      (results, item) => {
        Object.assign(results, {
          [item.name as string]: item.meta?.navName,
        });
        return results;
      },
      {} as Record<string, string>,
    ),
  );

  watch(
    () => route.name,
    (name) => {
      toolboxTitle.value = titleMap.value[name as string];
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .toolbox-title-box {
    display: flex;
    width: 100%;
    height: 54px;
    padding: 0 24px;
    align-items: center;

    .title {
      margin-right: 8px;
      font-size: 14px;
      font-weight: 700;
      color: #313238;
    }
  }
</style>
