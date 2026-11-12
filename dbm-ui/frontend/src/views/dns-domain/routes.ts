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

import { getDnsDomainEnabled } from '@services/source/dnsDomain';

import { registerModule } from '@router';

import { t } from '@locales/index';

/**
 * 域名服务：仅内部上云环境通过 URL 访问，DBM 不设入口。
 * 路由 name 刻意不登记进 layout/Index.vue 的 routeGroup：顶栏不高亮、左侧菜单不渲染，页面自带页面内导航
 */
export default function getRoutes() {
  registerModule([
    {
      path: 'dns-domain/:page?',
      name: 'DnsDomain',
      meta: {
        fullscreen: true,
        navName: t('域名服务'),
      },
      // 未开放环境跳转「数据库管理」默认页。
      // 依赖 db-manage/mysql/routes.ts 的 DatabaseTendbha，当前业务未启用 MySQL 时由数据库管理菜单的 useActiveKey 兜底到该业务默认页
      beforeEnter: () =>
        getDnsDomainEnabled()
          .then((data) => (data.enabled ? true : { name: 'DatabaseTendbha' }))
          .catch(() => ({ name: 'DatabaseTendbha' })),
      component: () => import('@views/dns-domain/Index.vue'),
    },
  ]);
}
