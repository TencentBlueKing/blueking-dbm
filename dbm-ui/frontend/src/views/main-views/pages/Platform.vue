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
  <MainView>
    <template #menu>
      <BkMenu
        :active-key="activeKey"
        :collapse="menuStore.collapsed"
        @click="handleChangeMenu"
        @mouseenter="menuStore.mouseenter"
        @mouseleave="menuStore.mouseleave">
        <div class="main-menu__list db-scroll-y">
          <BkMenuGroup :name="$t('配置管理')">
            <BkMenuItem key="PlatConf">
              <template #icon>
                <i class="db-icon-db-config" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('数据库配置') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup :name="$t('事件中心')">
            <BkMenuItem key="PlatDBMASwitchEvents">
              <template #icon>
                <i class="db-icon-db-config" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('DBHA切换事件') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup :name="$t('文件管理')">
            <BkMenuItem key="PlatformVersionFiles">
              <template #icon>
                <i class="db-icon-version" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('版本文件') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup :name="$t('资源管理')">
            <BkMenuItem key="ResourceSpec">
              <template #icon>
                <i class="db-icon-version" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('资源规格管理') }}
              </span>
            </BkMenuItem>
            <!-- <BkMenuItem key="deploymentPlanManage">
              <template #icon>
                <i class="db-icon-version" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('部署方案') }}
              </span>
            </BkMenuItem> -->
            <BkMenuItem key="resourcePoolManage">
              <template #icon>
                <i class="db-icon-version" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('DB 资源池') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup :name="$t('设置')">
            <BkSubmenu
              key="platform-mysql"
              title="MySQL">
              <template #icon>
                <i class="db-icon-mysql" />
              </template>
              <BkMenuItem key="PlatformWhitelist">
                <!-- <template #icon>
                  <i class="db-icon-list" />
                </template> -->
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ $t('授权白名单') }}
                </span>
              </BkMenuItem>
              <BkMenuItem key="PlatformPasswordPolicy">
                <!-- <template #icon>
                  <i class="db-icon-password" />
                </template> -->
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ $t('密码安全规则') }}
                </span>
              </BkMenuItem>
            </BkSubmenu>
            <BkMenuItem key="PlatformStaff">
              <template #icon>
                <i class="db-icon-dba-config" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('DBA人员管理') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
        </div>
        <MenuToggleIcon />
      </BkMenu>
    </template>
  </MainView>
</template>

<script setup lang="ts">
  import { useMenu } from '@stores';

  import MainView from '@components/layouts/MainView.vue';

  import MenuToggleIcon from '../components/MenuToggleIcon.vue';
  import { useMenuInfo } from '../hooks/useMenuInfo';

  const menuStore = useMenu();
  const { activeKey, handleChangeMenu } = useMenuInfo();
</script>
