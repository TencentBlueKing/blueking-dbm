/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/

import type { RouteLocationNormalizedLoaded, RouteRecordRaw } from 'vue-router';

export const useMenuInfo = () => {
  const route = useRoute();
  const router = useRouter();

  // 获取 menu 相关配置
  const { children } = route.matched[0];
  const routes = computed(() => children.reduce((routes: RouteRecordRaw[], route) => (
    routes.concat([route, ...route.children || []])
  ), []));

  // 获取 menu 默认激活信息
  const activeMenu = computed<RouteLocationNormalizedLoaded | RouteRecordRaw | undefined>(() => {
    const { activeMenu } = route.meta;
    if (activeMenu) {
      return routes.value.find((route: RouteRecordRaw) => route.name === activeMenu);
    }

    return route;
  });
  const activeKey = computed(() => activeMenu.value?.name as string | undefined);
  const openedKeys = computed(() => (activeMenu.value?.meta?.submenuId ? [activeMenu.value.meta.submenuId] : []));

  /** menu 点击事件 */
  const handleChangeMenu = ({ key }: any) => {
    if (key === route.name) return;
    router.push({ name: key });
  };

  return {
    activeKey,
    openedKeys,
    handleChangeMenu,
  };
};
