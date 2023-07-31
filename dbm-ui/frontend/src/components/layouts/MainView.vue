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
  <div class="main-container">
    <div
      class="main-menu"
      :class="[{ 'main-menu--collapsed': menuStore.toggleCollapsed }]">
      <slot name="menu" />
    </div>
    <div class="main-container__content">
      <MainBreadcrumbs
        v-if="!mainViewStore.customBreadcrumbs"
        class="main-container__breadcrumbs" />
      <slot name="main-content">
        <div
          id="mainContainerView"
          class="main-container__view db-scroll-y db-scroll-x"
          :class="[{
            'pd-24': mainViewStore.hasPadding,
            'has-breadcrumbs': !mainViewStore.customBreadcrumbs
          }]">
          <!-- 这里是用 route.name 作为 key 是考虑到 repalce params/query 的使用 -->
          <!-- <RouterView :key="key" /> -->
          <RouterView />
        </div>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
  import {
    useMainViewStore,
    useMenu,
  } from '@stores';

  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  const mainViewStore = useMainViewStore();

  const menuStore = useMenu();
</script>

<style lang="less">
  @import "@styles/mixins.less";

  .main-container {
    display: flex;
    height: 100%;
  }

  .main-menu {
    position: relative;
    z-index: 101;
    height: 100%;
    background-color: #1e2634;
    flex-shrink: 0;

    &--collapsed {
      width: 60px;
    }

    .bk-menu {
      height: 100%;

      .submenu-header {
        flex-shrink: 0;
      }
    }

    &__list {
      height: calc(100vh - 108px);
      padding: 12px 0 4px;

      &.db-scroll-y {
        &::-webkit-scrollbar-thumb {
          background-color: #515560;
          border-radius: 4px;
        }

        &:hover {
          &::-webkit-scrollbar-thumb {
            background-color: #515560;
          }
        }
      }
    }

    &__toggle {
      .flex-center();

      width: 60px;
      height: 56px;
      padding-left: 14px;
      color: #96a2b9;
    }

    &__icon {
      .flex-center();

      width: 32px;
      height: 32px;
      font-size: @font-size-large;
      cursor: pointer;
      border-radius: 50%;
      transform: rotate(180deg);
      transition: all 0.2s;
      justify-content: center;

      &:hover {
        color: #d3d9e4;
        background: linear-gradient(270deg, #253047, #263247);
      }

      &--active {
        transform: rotate(0);
      }
    }

    &__count {
      height: 16px;
      padding: 0 8px;
      margin: 2px 4px 0 8px;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 12px;
      line-height: 16px;
      color: white;
      background-color: #333a47;
      border-radius: 30px;
    }

    .bk-menu-item.is-active {
      .main-menu__count {
        background-color: #4d8fff;
      }
    }
  }

  .main-container__content {
    position: relative;
    width: 0;
    height: 100%;
    min-width: 940px;
    flex: 1;
  }

  .main-container__view {
    height: 100%;
    background-color: #f5f7fa;

    &.has-breadcrumbs {
      height: calc(100% - 52px);
    }
  }
</style>
