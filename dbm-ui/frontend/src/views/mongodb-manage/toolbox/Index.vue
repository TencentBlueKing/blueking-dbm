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
  <BkResizeLayout
    :border="false"
    class="mongo-manage-toolbox-page"
    collapsible
    disabled
    initial-divide="300px">
    <template #aside>
      <ToolboxSide />
    </template>
    <template #main>
      <div class="toolbox-page-wrapper">
        <div class="toolbox-page-title">
          <span style="font-weight: bold;">{{ toolboxTitle }}</span>
          <BkTag
            class="ml-8"
            theme="info">
            MongDB
          </BkTag>
        </div>
        <div class="toolbox-content-wrapper">
          <ScrollFaker style="padding: 0 24px">
            <RouterView />
          </ScrollFaker>
        </div>
      </div>
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { watch } from 'vue';
  import { useRoute } from 'vue-router';

  import ToolboxSide from './components/toolbox-side/Index.vue';

  const route = useRoute();

  const toolboxTitle = ref('');

  watch(route, () => {
    toolboxTitle.value = route.meta.navName as string;
  }, {
    immediate: true,
  });
</script>
<style lang="less">
.mongo-manage-toolbox-page {
  height: 100%;

  & > .bk-resize-layout-aside {
    z-index: 100;

    &::after {
      display: none;
    }
  }

  .toolbox-page-wrapper {
    height: 100%;
    background-color: white;

    .toolbox-page-title {
      display: flex;
      width: 100%;
      height: 54px;
      padding: 0 24px;
      align-items: center;
      font-size: 14px;
      color: #313238;
    }

    .toolbox-content-wrapper {
      height: calc(100% - 52px);
    }
  }
}
</style>
