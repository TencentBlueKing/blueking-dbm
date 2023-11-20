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
  <BkLoading
    class="app-loading"
    :loading="globalBizsStore.loading">
    <BkNavigation
      class="main-navigation"
      default-open
      :hover-width="240"
      navigation-type="top-bottom"
      :need-menu="false"
      :side-title="$t('PROJECT_TITLE_数据库管理')"
      theme-color="#1e2634">
      <template #side-header>
        <RouterLink
          style="display: flex; align-items: center;"
          :to="{ name: MainViewRouteNames.SelfService }">
          <img
            height="30"
            src="@images/nav-logo.png"
            width="30">
          <span class="title-desc ml-8">{{ $t('PROJECT_TITLE_数据库管理') }}</span>
        </RouterLink>
      </template>
      <template #header>
        <div class="main-navigation__left">
          <RouterLink
            active-class="main-navigation__nav--active"
            class="main-navigation__nav"
            :to="{ name: MainViewRouteNames.SelfService }">
            {{ $t('服务自助') }}
          </RouterLink>
          <RouterLink
            active-class="main-navigation__nav--active"
            class="main-navigation__nav"
            :to="{
              name: MainViewRouteNames.Database,
              params: { bizId: globalBizsStore.currentBizId }
            }">
            {{ $t('数据库管理') }}
          </RouterLink>
          <AuthComponent
            action-id="GLOBAL_MANAGE"
            immediate-check>
            <RouterLink
              active-class="main-navigation__nav--active"
              class="main-navigation__nav"
              :to="{ name: MainViewRouteNames.Platform }">
              {{ $t('平台管理') }}
            </RouterLink>
          </AuthComponent>
        </div>
        <div class="main-navigation__right">
          <LocaleSwitch />
          <BkDropdown
            @hide="() => state.isShow = false"
            @show="() => state.isShow = true">
            <div class="user-info">
              <span class="user-info__name">{{ userProfileStore.username }}</span>
              <i
                class="db-icon-down-shape user-info__arrow"
                :class="[{ 'user-info__arrow--active': state.isShow }]" />
            </div>
            <template #content>
              <BkDropdownMenu>
                <BkDropdownItem @click="handleSignOut">
                  {{ $t('退出登录') }}
                </BkDropdownItem>
              </BkDropdownMenu>
            </template>
          </BkDropdown>
        </div>
      </template>
      <RouterView />
    </BkNavigation>
  </BkLoading>
  <LoginModel />
  <ResourceDetection />
  <PermissionDialog />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getLogout } from '@services/source/logout';

  import { useInfo, useSQLTaskNotify } from '@hooks';

  import { useGlobalBizs, useUserProfile } from '@stores';

  import LocaleSwitch from '@components/layouts/LocaleSwitch.vue';
  import LoginModel from '@components/layouts/Login.vue';
  import ResourceDetection from '@components/layouts/ResourceDetection.vue';
  import PermissionDialog from '@components/permission/Dialog.vue';

  import { MainViewRouteNames } from '@views/main-views/common/const';

  const state = reactive({
    isShow: false,
  });

  const { t, locale } = useI18n();
  const globalBizsStore = useGlobalBizs();

  /**
   * fetch user profile
   */
  const userProfileStore = useUserProfile();
  userProfileStore.fetchProfile();

  const documentTitles: Record<string, string> = {
    en: 'DBM | Tencent BlueKing',
    'zh-cn': '数据库管理 | 腾讯蓝鲸智云',
  };
  watch(locale, () => {
    document.title = documentTitles[locale.value];
  }, { immediate: true });

  /**
   * sign out
   */
  const handleSignOut = () => {
    useInfo({
      title: t('确认退出登录'),
      onConfirm: () => getLogout().then(() => {
        window.location.reload();
        return true;
      }),
    });
  };

  onMounted(() => {
    // sql 变更执行全局 notify
    useSQLTaskNotify();
  });
</script>
<style lang="less">
  @nav-main-color: #96a2b9;
  @nav-top-color: #0E1525;

  .app-loading {
    width: 100%;
    height: 100%;

    > .bk-loading-mask {
      z-index: 9998 !important;
      opacity: 100% !important;
    }

    > .bk-loading-indicator {
      z-index: 9999 !important;
    }
  }

  .main-navigation {
    .bk-navigation-header {
      background-color: @nav-top-color;
    }

    .header-right {
      justify-content: space-between;
    }

    .container-content {
      padding: 0 !important;
    }
  }

  .main-navigation__left {
    margin-left: 20px;
    line-height: 52px;
  }

  .main-navigation__nav {
    display: inline-block;
    margin-right: 32px;
    color: @nav-main-color;

    &:hover {
      color: #d3d9e4;
    }

    &.main-navigation__nav--active {
      color: @white-color;
    }
  }

  .main-navigation__right {
    color: @nav-main-color;

    .user-info {
      cursor: pointer;

      &__name {
        padding-right: 4px;
      }

      &__arrow {
        display: inline-block;
        font-size: @font-size-mini;
        transition: all 0.2s;

        &--active {
          transform: rotate(180deg);
        }
      }
    }
  }
</style>
