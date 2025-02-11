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
import _ from 'lodash';
import { createRouter, createWebHistory, type Router, type RouteRecordRaw } from 'vue-router';

import { useGlobalBizs } from '@stores';

import BizPermission from '@views/BizPermission.vue';
import getDbConfRoutes from '@views/db-configure/routes';
import getDbManageRoutes from '@views/db-manage/routes';
import getDbhaSwitchEventsRouters from '@views/dbha-switch-events/routes';
import getDutyRuleManageRoutes from '@views/duty-rule-manage/routes';
import getInspectionRoutes from '@views/inspection-manage/routes';
import getDBMonitorAlarmRoutes from '@views/monitor-alarm-db/routes';
import getPlatMonitorAlarmRoutes from '@views/monitor-alarm-plat/routes';
import getNotificationSettingRoutes from '@views/notification-setting/routes';
import getPasswordManageRoutes from '@views/password-manage/routes';
import getPlatformDbConfigureRoutes from '@views/platform-db-configure/routes';
import getQuickSearchRoutes from '@views/quick-search/routes';
import getResourceManageRoutes from '@views/resource-manage/routes';
import getServiceApplyRoutes from '@views/service-apply/routes';
import getStaffManageRoutes from '@views/staff-manage/routes';
import getTaskHistoryRoutes from '@views/task-history/routes';
import getTemporaryPasswordModify from '@views/temporary-paassword-modify/routes';
import getTicketRoutes from '@views/ticket-center/routes';
import getTicketCooperationSettingRoutes from '@views/ticket-cooperation-setting/routes';
import getTicketFlowSettingBizRoutes from '@views/ticket-flow-setting-biz/routes';
import getTicketFlowSettingGlobalRoutes from '@views/ticket-flow-setting-global/routes';
import getTicketNoticeRoutes from '@views/ticket-notice-setting/routes';
import getVersionFilesRoutes from '@views/version-files/routes';
import getWhitelistRoutes from '@views/whitelist/routes';

import { checkDbConsole } from '@utils';

import { connectToMain, rootPath } from '@blueking/sub-saas';

let appRouter: Router;

const renderPageWithComponent = (route: RouteRecordRaw, component: typeof BizPermission) => {
  if (route.component) {
    // eslint-disable-next-line no-param-reassign
    route.component = component;
  }
  if (route.children) {
    route.children.forEach((item) => {
      renderPageWithComponent(item, component);
    });
  }
};

const moduleList: RouteRecordRaw[] = [];
export const registerModule = (routeList: RouteRecordRaw[]) => {
  moduleList.push(...routeList);
};

const businessModuleList: RouteRecordRaw[] = [];
export const registerBusinessModule = (routeList: RouteRecordRaw[]) => {
  businessModuleList.push(...routeList);
};

export default () => {
  // 解析业务id
  // 1,url中包含业务id
  // 2,本地缓存中包含业务id
  // 3,业务列表中的第一个业务
  const { bizs: bizList } = useGlobalBizs();
  const pathBiz = window.location.pathname.match(/^\/(\d+)\/?/);
  let currentBiz = '';
  if (pathBiz) {
    [, currentBiz] = pathBiz;
  } else {
    const localCacheBizId = Number(localStorage.getItem('lastBizId'));
    if (localCacheBizId) {
      currentBiz = `${localCacheBizId}`;
    } else {
      const headBiz = _.head(bizList);
      if (headBiz) {
        currentBiz = `${headBiz.bk_biz_id}`;
      }
    }
  }
  useGlobalBizs().changeBizId(Number(currentBiz));
  window.PROJECT_CONFIG.BIZ_ID = Number(currentBiz);
  localStorage.setItem('lastBizId', currentBiz);

  let bizPermission = false;
  const bizInfo = _.find(bizList, (item) => item.bk_biz_id === Number(currentBiz));
  if (bizInfo && bizInfo.permission.db_manage) {
    bizPermission = true;
  }

  getTicketRoutes();
  getTaskHistoryRoutes();
  getInspectionRoutes();

  const routes = [
    {
      path: rootPath,
      name: 'index',
      redirect: {
        name: checkDbConsole('personalWorkbench.serviceApply') ? 'MyTodos' : 'DatabaseTendbha',
      },
      children: [
        ...getResourceManageRoutes(),
        ...getVersionFilesRoutes(),
        ...getPlatformDbConfigureRoutes(),
        ...getPasswordManageRoutes(),
        ...getServiceApplyRoutes(),
        ...getQuickSearchRoutes(),
        ...getDutyRuleManageRoutes(),
        ...moduleList,
      ],
    },
    {
      path: `${rootPath}${currentBiz}`,
      children: [
        ...getDbManageRoutes(),
        ...getDbConfRoutes(),
        ...getDbhaSwitchEventsRouters(),
        ...getDBMonitorAlarmRoutes(),
        ...getPlatMonitorAlarmRoutes(),
        ...getNotificationSettingRoutes(),
        ...getStaffManageRoutes(),
        ...getWhitelistRoutes(),
        // ...getTicketManageRoutes(),
        ...getTemporaryPasswordModify(),
        ...getTicketFlowSettingBizRoutes(),
        ...getTicketCooperationSettingRoutes(),
        ...getTicketFlowSettingGlobalRoutes(),
        ...businessModuleList,
        ...getTicketNoticeRoutes(),
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: '404',
      component: () => import('@views/404.vue'),
    },
  ];

  console.log('routes = ', routes);

  if (!bizPermission) {
    renderPageWithComponent(routes[1], BizPermission);
  }

  appRouter = createRouter({
    history: createWebHistory(),
    routes,
  });
  connectToMain(appRouter);

  let lastRouterHrefCache = '/';
  const routerPush = appRouter.push;
  const routerReplace = appRouter.replace;

  appRouter.push = (params) => {
    lastRouterHrefCache = appRouter.resolve(params).href;
    return routerPush(params);
  };
  appRouter.replace = (params) => {
    lastRouterHrefCache = appRouter.resolve(params).href;
    return routerReplace(params);
  };

  if (import.meta.env.MODE === 'production') {
    appRouter.onError((error: any) => {
      if (/Failed to fetch dynamically imported module/.test(error.message)) {
        window.location.href = lastRouterHrefCache;
      }
    });
  }

  return appRouter;
};

export const getRouter = () => appRouter;
