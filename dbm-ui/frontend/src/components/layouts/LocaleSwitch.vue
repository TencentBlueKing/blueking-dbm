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
  <BkDropdown
    @hide="() => isShow = false"
    @show="() => isShow = true">
    <div
      class="locale-info"
      :class="{ 'active': isShow }">
      <DbIcon :type="$i18n.locale === 'en' ? 'en' : 'cn'" />
    </div>
    <template #content>
      <BkDropdownMenu class="locale-switch">
        <BkDropdownItem
          :class="{'active': $i18n.locale ==='en'}"
          @click="handleSwitchLocale('en')">
          <DbIcon type="en" />
          English
        </BkDropdownItem>
        <BkDropdownItem
          :class="{'active': $i18n.locale === 'zh-cn'}"
          @click="handleSwitchLocale('zh-cn')">
          <DbIcon type="cn" />
          中文
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script setup lang="ts">
  import Cookies from 'js-cookie';

  import I18n from '@locales/index';

  const isShow = ref(false);

  const handleSwitchLocale = (locale: string) => {
    Cookies.set('blueking_language', locale, {
      expires: 3600,
      domain: window.location.hostname
        .split('.')
        .slice(-2)
        .join('.'),
    });
    I18n.global.locale.value = locale;
    document.querySelector('html')?.setAttribute('lang', locale);
    window.location.reload();
  };
</script>

<style lang="less" scoped>
  .locale-info {
    width: 32px;
    height: 32px;
    margin-right: 16px;
    font-size: 16px;
    line-height: 32px;
    text-align: center;
    cursor: pointer;
    border-radius: 50%;

    &:hover,
    &.active {
      color: @primary-color;
      background-color: #f0f1f5;
    }
  }
</style>

<style lang="less">
  .locale-switch {
    .bk-dropdown-item {
      i {
        font-size: 14px;
      }

      &.active {
        color: @primary-color;
        background-color: #eaf3ff;
      }
    }
  }
</style>
