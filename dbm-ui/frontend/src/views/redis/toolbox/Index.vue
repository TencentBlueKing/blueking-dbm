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
  <MainBreadcrumbs>
    <span class="custom-breadcrumbs">{{ $t('Redis_工具箱') }}</span>
  </MainBreadcrumbs>
  <BkResizeLayout
    :border="false"
    class="toolbox"
    collapsible
    disabled
    initial-divide="300px">
    <template #aside>
      <ToolboxSide />
    </template>
    <template #main>
      <ToolboxContent />
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import { useMainViewStore } from '@stores';

  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  import ToolboxContent from './components/ToolboxContent.vue';
  import ToolboxSide from './components/ToolboxSide.vue';

  const route = useRoute();

  watch(() => route.fullPath, () => {
    if (route.fullPath.includes('redis-toolbox')) {
      const mainViewStore = useMainViewStore();
      mainViewStore.hasPadding = false;
      mainViewStore.customBreadcrumbs = true;
    }
  }, { immediate: true });
</script>

<style lang="less" scoped>
.custom-breadcrumbs {
  font-size: @font-size-large;
  color: @title-color;
}

.toolbox {
  height: calc(100% - 52px);

  & > :deep(.bk-resize-layout-aside) {
    z-index: 100;

    &::after {
      display: none;
    }
  }
}
</style>
