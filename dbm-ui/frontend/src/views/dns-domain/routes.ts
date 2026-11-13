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

import { getSystemEnviron } from '@services/source/systemSettings';

import { registerModule } from '@router';

import { useSystemEnviron } from '@stores';

import { t } from '@locales/index';

/**
 * 读取系统环境变量：main.ts 启动时已触发加载，但 fetchSystemEnviron 不返回 Promise，
 * 直接打开本页时首次路由守卫可能早于响应，此时 store 为空，补发一次请求
 */
const loadSystemEnviron = () => {
  const { urls } = useSystemEnviron();
  return Object.keys(urls).length > 0 ? Promise.resolve(urls) : getSystemEnviron();
};

/**
 * 域名服务：仅内部上云环境通过 URL 访问，DBM 顶栏不设入口。
 * 父路由 name 登记在 layout/Index.vue 的 routeGroup（dnsDomain 分组）用于渲染左侧菜单，该分组不在顶栏 menuList 中
 */
export default function getRoutes() {
  registerModule([
    {
      path: 'dns-domain',
      name: 'DnsDomain',
      // 是否开放由系统环境变量 DNS_DOMAIN_SERVICE_ENABLED 决定，未开放或读取失败时跳转「数据库管理」默认页。
      // 依赖 db-manage/mysql/routes.ts 的 DatabaseTendbha，当前业务未启用 MySQL 时由数据库管理菜单的 useActiveKey 兜底到该业务默认页。
      // 守卫挂在父路由上，子路由之间切换不会重复执行
      beforeEnter: () =>
        loadSystemEnviron()
          .then((environ) => (environ.DNS_DOMAIN_SERVICE_ENABLED === true ? true : { name: 'DatabaseTendbha' }))
          .catch(() => ({ name: 'DatabaseTendbha' })),
      redirect: {
        name: 'DnsDomainList',
      },
      component: () => import('@views/dns-domain/Index.vue'),
      children: [
        {
          path: 'domains',
          name: 'DnsDomainList',
          meta: {
            navName: t('域名列表'),
          },
          component: () => import('@views/dns-domain/domain-list/Index.vue'),
        },
        {
          path: 'audits',
          name: 'DnsDomainAudit',
          meta: {
            navName: t('操作日志'),
          },
          component: () => import('@views/dns-domain/global-audit/Index.vue'),
        },
      ],
    },
  ]);
}
