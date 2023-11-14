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
  <div class="main-breadcrumbs">
    <slot>
      <i
        v-if="showBack"
        class="db-icon-arrow-left main-breadcrumbs__back"
        @click="handleBack" />
      <span class="main-breadcrumbs__current">
        <span>{{ current }}</span>
        <span id="dbmPageSubtitle" />
      </span>
      <template v-if="tags.length !== 0">
        <BkTag
          v-for="(tag, index) of tags"
          :key="index"
          :theme="tag.theme">
          {{ tag.text }}
        </BkTag>
      </template>
    </slot>
    <slot name="append" />
  </div>
</template>

<script setup lang="ts">
  import { useMainViewStore } from '@stores';

  const store = useMainViewStore();
  const route = useRoute();
  const router = useRouter();

  /**
   * 当前面包屑展示文案
   */
  const current = computed(() => store.breadCrumbsTitle || route.meta.navName);

  /**
   * tags
   */
  const tags = computed(() => {
    if (store.tags.length !== 0) {
      return store.tags;
    }

    if (route.meta.tags && route.meta.tags.length !== 0) {
      return route.meta.tags;
    }

    return [];
  });

  /**
   * back control
   */
  const showBack = computed(() => !route.meta.isMenu && [undefined, true].includes(route.meta.showBack));
  const handleBack = () => {
    const { back } = window.history.state;
    if (back) {
      router.go(-1);
    } else {
      const { matched } = route;
      const count = matched.length;
      if (count > 1) {
        const backRoute = matched[count - 1];
        router.push({ name: backRoute.meta.activeMenu });
      }
    }
  };
</script>

<style lang="less">
  @import "@styles/mixins";

  .main-breadcrumbs {
    .flex-center();

    position: relative;
    z-index: 101;
    width: 100%;
    height: 52px;
    padding: 0 24px;
    background-color: @white-color;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    &__back {
      margin-right: 16px;
      font-size: @font-size-large;
      color: @primary-color;
      cursor: pointer;
    }

    &__current {
      margin-right: 8px;
      font-size: @font-size-large;
      color: @title-color;
    }

    .bk-tag {
      margin-right: 4px;
    }
  }
</style>
