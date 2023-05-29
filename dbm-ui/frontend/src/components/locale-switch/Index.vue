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
  <BkPopover
    placement="bottom"
    theme="light local-switch-menu-theme"
    @after-hidden="isShow = false"
    @after-show="isShow = true">
    <div
      class="locale-info"
      :class="{ active: isShow }">
      <DbIcon :type="$i18n.locale === 'en' ? 'en' : 'cn'" />
    </div>
    <template #content>
      <div class="local-switch-menu">
        <div
          class="item"
          :class="{
            active: $i18n.locale === 'en',
          }"
          @click="handleSwitchLocale('en')">
          <DbIcon
            class="mr-4"
            type="en" />
          English
        </div>
        <div
          class="item"
          :class="{ active: $i18n.locale === 'zh-cn' }"
          @click="handleSwitchLocale('zh-cn')">
          <DbIcon
            class="mr-4"
            type="cn" />
          中文
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import Cookies from 'js-cookie';

  import { useSystemEnviron } from '@stores';

  import I18n from '@locales/index';

  const systemEnvironStore = useSystemEnviron();

  const isShow = ref(false);

  const handleSwitchLocale = (locale: string) => {
    const { BK_COMPONENT_API_URL, BK_DOMAIN } = systemEnvironStore.urls;
    const api = `${BK_COMPONENT_API_URL}/api/c/compapi/v2/usermanage/fe_update_user_language/`;

    const scriptId = 'jsonp-script';
    const prevJsonpScript = document.getElementById(scriptId);
    if (prevJsonpScript) {
      document.body.removeChild(prevJsonpScript);
    }
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = `${api}?language=${locale}`;
    script.id = scriptId;
    document.body.appendChild(script);

    Cookies.set('blueking_language', locale, {
      expires: 3600,
      domain: BK_DOMAIN,
    });
    I18n.global.locale.value = locale as any;
    document.querySelector('html')?.setAttribute('lang', locale);
    window.location.reload();
  };
</script>
<style lang="less" scoped>
  .locale-info {
    position: relative;
    display: inline-flex;
    width: 32px;
    height: 32px;
    margin-right: 8px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    border-radius: 50%;
    transition: background 0.15s;
    align-items: center;
    justify-content: center;

    &:hover,
    &.active {
      color: @primary-color;
      background-color: #f0f1f5;
    }
  }
</style>

<style lang="less">
  .bk-popover[data-theme~='local-switch-menu-theme'] {
    padding-right: 0 !important;
    padding-left: 0 !important;

    .item {
      display: flex;
      height: 32px;
      padding: 0 16px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      align-items: center;

      &.active,
      &:hover {
        color: #3a84ff;
        background-color: #eaf3ff;
      }
    }

    .lang-flag {
      margin-right: 4px;
      font-size: 20px;
    }
  }
</style>
