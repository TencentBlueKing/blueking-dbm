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
  <Error v-if="globalBizsStore.isError" />
  <BizPermission v-else-if="notExistBusiness" />
  <MainView v-else>
    <template #menu>
      <BkMenu
        :active-key="activeKey"
        :collapse="menuStore.collapsed"
        :opened-keys="openedKeys"
        @click="handleChangeMenu"
        @mouseenter="menuStore.mouseenter"
        @mouseleave="menuStore.mouseleave">
        <div class="main-menu__list db-scroll-y">
          <AppSelector :collapsed="menuStore.collapsed" />
          <BkMenuGroup name="MySQL">
            <BkMenuItem key="DatabaseTendbsingle">
              <template #icon>
                <i class="db-icon-node" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('单节点') }}
              </span>
            </BkMenuItem>
            <BkSubmenu
              key="database-tendbha-cluster"
              :title="$t('高可用集群')">
              <template #icon>
                <i class="db-icon-cluster" />
              </template>
              <BkMenuItem key="DatabaseTendbha">
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ $t('集群视图') }}
                </span>
              </BkMenuItem>
              <BkMenuItem key="DatabaseTendbhaInstance">
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ $t('实例视图') }}
                </span>
              </BkMenuItem>
            </BkSubmenu>
            <BkSubmenu
              key="database-permission"
              :title="$t('权限管理')">
              <template #icon>
                <i class="db-icon-history" />
              </template>
              <BkMenuItem key="PermissionRules">
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ $t('授权规则') }}
                </span>
              </BkMenuItem>
              <BkMenuItem key="DatabaseWhitelist">
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ $t('授权白名单') }}
                </span>
              </BkMenuItem>
            </BkSubmenu>
            <BkMenuItem key="MySQLToolbox">
              <template #icon>
                <i class="db-icon-tools" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('工具箱') }}
              </span>
            </BkMenuItem>
            <BkSubmenu
              v-for="group of toolboxFavorMenus"
              :key="group.id"
              :title="group.name">
              <template #icon>
                <i :class="group.icon" />
              </template>
              <BkMenuItem
                v-for="item of group.children"
                :key="item.name">
                <span
                  v-overflow-tips.right
                  class="text-overflow">
                  {{ item.meta?.navName }}
                </span>
              </BkMenuItem>
            </BkSubmenu>
          </BkMenuGroup>
          <BkMenuGroup name="Redis">
            <BkMenuItem key="DatabaseRedis">
              <template #icon>
                <i class="db-icon-redis" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('集群管理') }}
              </span>
            </BkMenuItem>
            <BkMenuItem key="RedisToolbox">
              <template #icon>
                <i class="db-icon-tools" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('工具箱') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup name="ES">
            <BkMenuItem key="EsManage">
              <template #icon>
                <i class="db-icon-es" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('集群管理') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup name="HDFS">
            <BkMenuItem key="HdfsManage">
              <template #icon>
                <i class="db-icon-hdfs" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('集群管理') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup name="Kafka">
            <BkMenuItem key="KafkaManage">
              <template #icon>
                <i class="db-icon-kafka" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('集群管理') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup name="Pulsar">
            <BkMenuItem key="PulsarManage">
              <template #icon>
                <i class="db-icon-pulsar" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('集群管理') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup name="InfluxDB">
            <BkMenuItem key="InfluxDBInstances">
              <template #icon>
                <i class="db-icon-influxdb" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('实例管理') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup :name="$t('配置管理')">
            <BkMenuItem key="DatabaseConfig">
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
          <BkMenuGroup :name="$t('任务中心')">
            <BkMenuItem key="DatabaseMission">
              <template #icon>
                <i class="db-icon-history" />
              </template>
              <span
                v-overflow-tips.right
                class="text-overflow">
                {{ $t('历史任务') }}
              </span>
            </BkMenuItem>
          </BkMenuGroup>
          <BkMenuGroup :name="$t('设置')">
            <BkMenuItem key="DatabaseStaff">
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
    <template
      v-if="!biz?.permission?.db_manage"
      #main-content>
      <BizPermission />
    </template>
  </MainView>
</template>

<script setup lang="ts">
  import type { RouteRecordRaw } from 'vue-router';

  import { useGlobalBizs, useMenu, useUserProfile  } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import AppSelector from '@components/app-selector/index.vue';
  import MainView from '@components/layouts/MainView.vue';

  import BizPermission from '@views/exception/BizPermission.vue';
  import Error from '@views/exception/Error.vue';
  import { toolboxRoutes } from '@views/mysql/routes';
  import toolboxMenus, { type MenuChild } from '@views/mysql/toolbox/common/menus';

  import MenuToggleIcon from '../components/MenuToggleIcon.vue';
  import { useMenuInfo } from '../hooks/useMenuInfo';

  interface ToolboxMenuGroup {
    children: RouteRecordRaw[];
    name: string;
    id: string;
    icon: string;
  }

  const menuStore = useMenu();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const userProfileStore = useUserProfile();
  const { activeKey, handleChangeMenu, openedKeys } = useMenuInfo();

  const biz = computed(() => globalBizsStore.bizs.find(item => item.bk_biz_id === Number(route.params.bizId)));
  const notExistBusiness = computed(() => globalBizsStore.bizs.length === 0 && !biz.value);

  // 工具箱收藏导航
  const toolboxFavorMenus = computed(() => {
    const favors: Array<MenuChild> = userProfileStore.profile[UserPersonalSettings.MYSQL_TOOLBOX_FAVOR] || [];
    if (favors.length === 0) return [];

    const menuGroup: ToolboxMenuGroup[] = toolboxMenus.map(item => ({
      ...item,
      children: [],
    }));
    const routesMap: Record<string, Array<RouteRecordRaw>> = {};
    for (const item of favors) {
      const curRoute = toolboxRoutes.find(toolboxRoute => toolboxRoute.name === item.id);
      if (curRoute && routesMap[item.parentId]) {
        routesMap[item.parentId].push(curRoute);
      } else if (curRoute) {
        routesMap[item.parentId] = [curRoute];
      }
      // 动态设置 activeMenu
      if (curRoute?.meta) {
        curRoute.meta.activeMenu = undefined;
      }
    }
    for (const key of Object.keys(routesMap)) {
      const menus = menuGroup.find(item => item.id === key);
      if (menus) {
        menus.children = routesMap[key];
      }
    }
    return menuGroup.filter(item => item.children.length > 0);
  });
</script>
