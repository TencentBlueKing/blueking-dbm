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

import { connectToMain, rootPath } from '@blueking/sub-saas';

import { useGlobalBizs } from '@stores';

import getAiChatRoutes from '@views/ai-chat/routes';
import getBackupStorageRoutes from '@views/backup-storage/routes';
import BizPermission from '@views/BizPermission.vue';
import getDashborderRoutes from '@views/dashboard-manage/routes';
import getDbConfRoutes from '@views/db-configure/routes';
import getDbManageRoutes from '@views/db-manage/routes';
import getDbhaSwitchEventsRouters from '@views/dbha-switch-events/routes';
import getDutyRuleManageRoutes from '@views/duty-rule-manage/routes';
import getExerciseReportRoutes from '@views/exercise-report/routes';
import getInspectionRoutes from '@views/inspection-manage/routes';
import getMonitorAlarmRoutes from '@views/monitor-alarm/routes';
import getNotificationSettingRoutes from '@views/notification-setting/routes';
import getPasswordManageRoutes from '@views/password-manage/routes';
import getPlatformDbConfigureRoutes from '@views/platform-db-configure/routes';
import getQuickSearchRoutes from '@views/quick-search/routes';
import getResourceManageRoutes from '@views/resource-manage/routes';
import getRiskMemoRoutes from '@views/risk-memo/routes';
import getServiceApplyRoutes from '@views/service-apply/routes';
import getServiceStatusRoutes from '@views/service-status/routes';
import getStaffManageRoutes from '@views/staff-manage/routes';
import getTaskHistoryRoutes from '@views/task-history/routes';
import getTemporaryPasswordModify from '@views/temporary-paassword-modify/routes';
import getTicketRoutes from '@views/ticket-center/routes';
import getTodoRemindRoutes from '@views/todo-remind/routes';
import getVersionFilesRoutes from '@views/version-files/routes';
import getWhitelistRoutes from '@views/whitelist/routes';

import { checkDbConsole } from '@utils';

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
  if (bizInfo?.permission.db_manage) {
    bizPermission = true;
  }

  getTicketRoutes();
  getTaskHistoryRoutes();
  getInspectionRoutes();
  getMonitorAlarmRoutes();
  getResourceManageRoutes();
  getDashborderRoutes();
  getDbManageRoutes();
  getRiskMemoRoutes();
  getAiChatRoutes();
  getStaffManageRoutes();

  const routes = [
    {
      children: [
        ...getVersionFilesRoutes(),
        ...getPlatformDbConfigureRoutes(),
        ...getPasswordManageRoutes(),
        ...getServiceApplyRoutes(),
        ...getQuickSearchRoutes(),
        ...getDutyRuleManageRoutes(),
        ...getServiceStatusRoutes(),
        ...getExerciseReportRoutes(),
        ...getTodoRemindRoutes(),
        ...moduleList,
        {
          component: () => import('@/demo/Index.vue'),
          path: 'demo',
        },
      ],
      name: 'index',
      path: rootPath,
      redirect: {
        name: checkDbConsole('personalWorkbench.serviceApply') ? 'MyTodos' : 'DatabaseTendbha',
      },
    },
    {
      children: [
        ...getDbConfRoutes(),
        ...getDbhaSwitchEventsRouters(),
        ...getBackupStorageRoutes(),
        ...getNotificationSettingRoutes(),
        ...getWhitelistRoutes(),
        ...getTemporaryPasswordModify(),
        ...businessModuleList,
      ],
      path: `${rootPath}${currentBiz}`,
    },
    {
      component: () => import('@views/404.vue'),
      name: '404',
      path: '/:pathMatch(.*)*',
    },
  ];

  console.log('routes = ', routes);

  if (!bizPermission) {
    renderPageWithComponent(routes[1]!, BizPermission);
  }

  // BK_SITE_PATH 由后端模板注入，为 / 或 /dbm/ 形式的站点根路径，未注入时（本地开发）回退为 /
  const routerBase = window.BK_SITE_PATH && !window.BK_SITE_PATH.includes('{{') ? window.BK_SITE_PATH : '/';

  appRouter = createRouter({
    history: createWebHistory(routerBase),
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
