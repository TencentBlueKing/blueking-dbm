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
  <div class="toolbox-main">
    <MainBreadcrumbs>
      <template #append>
        <BkTag theme="info">
          Redis
        </BkTag>
      </template>
    </MainBreadcrumbs>
    <div class="toolbox-content db-scroll-y">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';
</script>

<style lang="less" scoped>
  .toolbox-main {
    height: 100%;
    background-color: white;

    :deep(.main-breadcrumbs) {
      z-index: 10;
      box-shadow: unset;

      &__current {
        font-size: @font-size-normal;
        font-weight: bold;
      }
    }

    .toolbox-content {
      height: calc(100% - 52px);
      padding: 0 24px;
    }
  }
</style>
