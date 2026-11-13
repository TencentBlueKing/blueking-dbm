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
  <DbMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <DbMenuGroup :name="t('域名服务')">
      <DbMenuItem
        icon="list"
        route-name="DnsDomainList">
        {{ t('域名列表') }}
      </DbMenuItem>
      <!-- 全局日志入口常驻，无 dns_audit_view 时置灰加锁，点击申请权限 -->
      <AuthTemplate
        action-id="dns_audit_view"
        class="dns-domain-menu-auth">
        <DbMenuItem
          icon="history"
          route-name="DnsDomainAudit">
          {{ t('操作日志') }}
        </DbMenuItem>
      </AuthTemplate>
    </DbMenuGroup>
  </DbMenu>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useActiveKey } from './hooks/useActiveKey';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';

  const { t } = useI18n();

  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const { key: currentActiveKey, parentKey, routeLocation: handleMenuChange } = useActiveKey(menuRef, 'DnsDomainList');
</script>
<style lang="less">
  .dns-domain-menu-auth {
    display: block;
  }
</style>
