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
  <div class="top-title">
    <MainBreadcrumbs>
      <span class="custom-breadcrumbs">{{ $t('TendbCluster_工具箱') }}</span>
    </MainBreadcrumbs>
  </div>
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
  import { onBeforeUnmount } from 'vue';

  import { useMainViewStore } from '@stores';

  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  import ToolboxContent from './components/ToolboxContent.vue';
  import ToolboxSide from './components/ToolboxSide.vue';

  const route = useRoute();
  const mainViewStore = useMainViewStore();

  watch(() => route.fullPath, () => {
    mainViewStore.hasPadding = false;
  }, {
    immediate: true,
  });

  onBeforeUnmount(() => {
    mainViewStore.hasPadding = true;
  });
</script>
<style lang="less" scoped>
.top-title {
  position: absolute;
  top: 0;
  left: 0;
}

.custom-breadcrumbs {
  font-size: @font-size-large;
  color: @title-color;
}

.toolbox {
  height: 100%;

  & > :deep(.bk-resize-layout-aside) {
    z-index: 100;

    &::after {
      display: none;
    }
  }
}
</style>
