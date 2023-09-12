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

import type { RouteRecordRaw } from 'vue-router';

interface ResolveNames {
  [key: string]: string
}

export interface MenuItem {
  isGroup: boolean,
  groupId?: string,
  groupName?: string,
  icon?: string,
  route?: RouteRecordRaw
  group?: MenuItem[]
}

export const getMenus = (
  routes: RouteRecordRaw[],
  key = 'group',
  isResolveNames: ResolveNames = {},
  menus: MenuItem[] = [],
) => {
  for (const route of routes) {
    const { meta, name } = route;
    const idKey = `${key}Id`;
    const nameKey = `${key}Name`;
    const groupId = meta?.[idKey] as string;
    const routeName = String(name);
    // 已经处理过直接结束本轮循环
    if (isResolveNames[routeName + key]) continue;

    if (groupId) {
      // 过滤出需要嵌套展示的路由
      const filterRoutes = routes.filter((filterRoute: RouteRecordRaw) => filterRoute.meta?.[idKey] === groupId);
      // 设置已经处理的路由
      filterRoutes.forEach((filterRoute: RouteRecordRaw) => {
        const filterRouteName = String(filterRoute.name);
        // eslint-disable-next-line
        return isResolveNames[filterRouteName + key] = filterRouteName
      });
      let group = [];
      // group -> submenu 只有两层不需要继续往下处理。
      if (key === 'submenu') {
        group = filterRoutes.map((filterRoute: RouteRecordRaw) => ({
          isGroup: false,
          route: filterRoute,
        }));
      } else {
        group = getMenus(filterRoutes, 'submenu', isResolveNames, []);
      }
      menus.push({
        isGroup: true,
        groupId,
        groupName: meta?.[nameKey] as string,
        group,
        icon: meta?.submenuIcon as string,
      });
      continue;
    }
    menus.push({
      isGroup: false,
      route,
    });
    // eslint-disable-next-line
    isResolveNames[routeName + key] = routeName;
  }
  return menus;
};
