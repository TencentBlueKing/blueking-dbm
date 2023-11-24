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
import {
  createRouter,
  createWebHistory,
  type Router,
} from 'vue-router';

import type {
  BigdataFunctions,
  MySQLFunctions,
  RedisFunctions,
} from '@services/model/function-controller/functionController';

import {
  useFunController,
  useGlobalBizs,
} from '@stores';

import getDbConfRoutes from '@views/db-configure/routes';
import getDbhaSwitchEventsRouters from '@views/dbha-switch-events/routes';
import getESRoutes from '@views/es-manage/routes';
import getHDFSRoutes from '@views/hdfs-manage/routes';
import getInfluxDBRoutes from '@views/influxdb-manage/routes';
import getInspectionRoutes from '@views/inspection-manage/routes';
import getKafkaRoutes from '@views/kafka-manage/routes';
import getDBMonitorAlarmRoutes from '@views/monitor-alarm-db/routes';
import getPlatMonitorAlarmRoutes from '@views/monitor-alarm-plat/routes';
import getMysqlRoutes from '@views/mysql/routes';
import getNotificationSettingRoutes from '@views/notification-setting/routes';
import getPasswordManageRoutes from '@views/password-manage/routes';
import getPlatformDbConfigureRoutes from '@views/platform-db-configure/routes';
import getPulsarRoutes from '@views/pulsar-manage/routes';
import getRedisRoutes from '@views/redis/routes';
import getResourceManageRoutes from '@views/resource-manage/routes';
import getRiakManage from '@views/riak-manage/routes';
import getServiceApplyRoutes from '@views/service-apply/routes';
import getSpiderManageRoutes from '@views/spider-manage/routes';
import getStaffSettingRoutes from '@views/staff-setting/routes';
import getTaskHistoryRoutes from '@views/task-history/routes';
import getTemporaryPasswordModify from '@views/temporary-paassword-modify/routes';
import getTicketManageRoutes from '@views/ticket-manage/routes';
import getTicketsRoutes from '@views/tickets/routes';
import getVersionFilesRoutes from '@views/version-files/routes';
import getWhitelistRoutes from '@views/whitelist/routes';

let appRouter: Router;
export default () => {
  // 解析 url 业务id
  const {
    bizs: bizList,
  } = useGlobalBizs();
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

  const { funControllerData } = useFunController();
  const mysqlController = funControllerData.getFlatData<MySQLFunctions, 'mysql'>('mysql');
  const redisController = funControllerData.getFlatData<RedisFunctions, 'redis'>('redis');
  const bigdataController = funControllerData.getFlatData<BigdataFunctions, 'bigdata'>('bigdata');

  appRouter = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/',
        name: 'index',
        redirect: {
          name: 'serviceApply',
        },
        children: [
          ...getResourceManageRoutes(),
          ...getVersionFilesRoutes(),
          ...getPlatformDbConfigureRoutes(),
          ...getPasswordManageRoutes(),
          ...getServiceApplyRoutes(),
        ],
      },
      {
        path: `/${currentBiz}`,
        children: [
          ...getDbConfRoutes(),
          ...getESRoutes(bigdataController),
          ...getDbhaSwitchEventsRouters(),
          ...getHDFSRoutes(bigdataController),
          ...getInfluxDBRoutes(bigdataController),
          ...getInspectionRoutes(),
          ...getKafkaRoutes(bigdataController),
          ...getDBMonitorAlarmRoutes(),
          ...getPlatMonitorAlarmRoutes(),
          ...getMysqlRoutes(mysqlController),
          ...getNotificationSettingRoutes(),
          ...getPulsarRoutes(bigdataController),
          ...getRedisRoutes(redisController),
          ...getSpiderManageRoutes(),
          ...getStaffSettingRoutes(),
          ...getTaskHistoryRoutes(),
          ...getTicketsRoutes(),
          ...getWhitelistRoutes(),
          ...getTicketManageRoutes(),
          ...getTemporaryPasswordModify(),
          ...getRiakManage(bigdataController),
        ],
      },
      {
        path: '/:pathMatch(.*)*',
        name: '404',
        component: () => import('@views/exception/404.vue'),
      },
    ],
  });

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

  appRouter.onError((error: any) => {
    if (/Failed to fetch dynamically imported module/.test(error.message)) {
      window.location.href = lastRouterHrefCache;
    }
  });

  return appRouter;
};

export const getRouter = () => appRouter;
