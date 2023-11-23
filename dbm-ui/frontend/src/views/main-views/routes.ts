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

import type {
  BigdataFunctions,
  MySQLFunctions,
  RedisFunctions,
} from '@services/model/function-controller/functionController';
import { checkAuthAllowed } from '@services/source/iam';

import { useFunController } from '@stores';

import { ClusterTypes } from '@common/const';

import getDbConfRoutes from '@views/db-configure/routes';
import getESRoutes from '@views/es-manage/routes';
import getEventCenterRouters from '@views/event-center/routes';
import getHDFSRoutes from '@views/hdfs-manage/routes';
import getInfluxDBRoutes from '@views/influxdb-manage/routes';
import getInspectionRoutes from '@views/inspection-manage/routes';
import getKafkaRoutes from '@views/kafka-manage/routes';
import getDBMonitorAlarmRoutes from '@views/monitor-alarm-db/routes';
import getPlatMonitorAlarmRoutes from '@views/monitor-alarm-plat/routes';
import getMysqlRoutes from '@views/mysql/routes';
import getNotificationSettingRoutes from '@views/notification-setting/routes';
import getPasswordPolicyRoutes from '@views/password-policy/routes';
import getPasswordRandomizationRoutes from '@views/password-randomization/routes';
import getPasswordTemporaryModify from '@views/password-temporary-modify/routes';
import getPlatformDbConfigureRoutes from '@views/platform-db-configure/routes';
import getPulsarRoutes from '@views/pulsar-manage/routes';
import getRedisRoutes from '@views/redis/routes';
import getResourcePool from '@views/resource-manage/routes';
import getResourceSpecRouters from '@views/resource-spec/routes';
import getServiceApplyRoutes from '@views/service-apply/routes';
import getSpiderManageRoutes from '@views/spider-manage/routes';
import getStaffSettingRoutes from '@views/staff-setting/routes';
import getTaskHistoryRoutes from '@views/task-history/routes';
import getTicketsRoutes from '@views/tickets/routes';
import getVersionFilesRoutes from '@views/version-files/routes';
import getWhitelistRoutes from '@views/whitelist/routes';

import { t } from '@locales/index';

import { MainViewRouteNames, type MainViewRouteNameValues } from './common/const';


const selfServiceRoute = {
  name: MainViewRouteNames.SelfService,
  path: '/self-service',
  redirect: {
    name: 'SelfServiceApply',
  },
  meta: {
    navName: t('服务自助'),
  },
  component: () => import('@views/main-views/pages/Services.vue'),
  children: [],
};

const dbmRoute: RouteRecordRaw = {
  name: MainViewRouteNames.Database,
  path: '/database/:bizId(\\d+)',
  meta: {
    navName: t('数据库管理'),
  },
  component: () => import('@views/main-views/pages/Database.vue'),
  children: [],
};

const platformRoute = {
  name: MainViewRouteNames.Platform,
  path: '/platform',
  redirect: {
    name: 'PlatformDbConfigure',
  },
  meta: {
    navName: t('平台管理'),
  },
  component: () => import('@views/main-views/pages/Platform.vue'),
  children: [],
};

const getMainRoutes = (routes: RouteRecordRaw[] = []) => {
  const mainRouteMap: Record<MainViewRouteNameValues, RouteRecordRaw> = {
    [MainViewRouteNames.SelfService]: selfServiceRoute,
    [MainViewRouteNames.Database]: dbmRoute,
    [MainViewRouteNames.Platform]: platformRoute,
  };

  for (const route of routes) {
    const { routeParentName } = route.meta || {};

    if (routeParentName && mainRouteMap[routeParentName as keyof typeof mainRouteMap]) {
      mainRouteMap[routeParentName as keyof typeof mainRouteMap]?.children?.push?.(route);
    }
  }

  return mainRouteMap;
};

const getAuthAllowed = checkAuthAllowed({
  action_ids: ['DB_MANAGE'],
  resources: [],
}).catch(() => [{
  action_id: '',
  is_allowed: false,
}]);

const dbmRouteRedirect = {
  redis: 'RedisManage',
  [ClusterTypes.TENDBSINGLE]: 'DatabaseTendbsingle',
  [ClusterTypes.TENDBHA]: 'DatabaseTendbha',
  [ClusterTypes.ES]: 'EsManage',
  [ClusterTypes.HDFS]: 'HdfsManage',
  [ClusterTypes.KAFKA]: 'KafkaManage',
  [ClusterTypes.PULSAE]: 'PulsarManage',
  [ClusterTypes.INFLUXDB]: 'InfluxDBManage',
};

export default async function getRouters() {
  const { fetchFunController } = useFunController();
  const [funController, authAllowed] = await Promise.all([fetchFunController(), getAuthAllowed]);
  const mysqlController = funController.getFlatData<MySQLFunctions, 'mysql'>('mysql');
  const redisController = funController.getFlatData<RedisFunctions, 'redis'>('redis');
  const bigdataController = funController.getFlatData<BigdataFunctions, 'bigdata'>('bigdata');

  const routes = [
    ...getMysqlRoutes(mysqlController),
    ...getRedisRoutes(redisController),
    ...getESRoutes(bigdataController),
    ...getHDFSRoutes(bigdataController),
    ...getKafkaRoutes(bigdataController),
    ...getPulsarRoutes(bigdataController),
    ...getInfluxDBRoutes(bigdataController),
    ...getSpiderManageRoutes(),
    ...getDbConfRoutes(),
    ...getTaskHistoryRoutes(),
    ...getPasswordPolicyRoutes(),
    ...getServiceApplyRoutes(),
    ...getStaffSettingRoutes(),
    ...getTicketsRoutes(),
    ...getVersionFilesRoutes(),
    ...getWhitelistRoutes(),
    ...getEventCenterRouters(),
    ...getResourcePool(),
    ...getResourceSpecRouters(),
    ...getDBMonitorAlarmRoutes(),
    ...getPlatMonitorAlarmRoutes(),
    ...getPasswordRandomizationRoutes(),
    ...getPasswordTemporaryModify(),
    ...getNotificationSettingRoutes(),
    ...getPasswordTemporaryModify(),
    ...getPlatformDbConfigureRoutes(),
    ...getInspectionRoutes(),
    // ...deploymentPlanRoutes,
  ];

  const mainRoutes = getMainRoutes(routes);

  const renderRoutes: RouteRecordRaw[] = [];

  for (const route of Object.values(mainRoutes)) {
    // 没开启平台管理功能
    if (route.name === MainViewRouteNames.Platform && !authAllowed[0]?.is_allowed) {
      continue;
    }

    // 处理导航重定向问题
    if (route.name === MainViewRouteNames.Database) {
      let name = '';
      if (mysqlController.tendbsingle) {
        name = dbmRouteRedirect.tendbsingle;
      } else if (mysqlController.tendbha) {
        name = dbmRouteRedirect.tendbha;
      } else if (redisController.redis) {
        name = dbmRouteRedirect.redis;
      } else if (bigdataController.es) {
        name = dbmRouteRedirect.es;
      } else if (bigdataController.hdfs) {
        name = dbmRouteRedirect.hdfs;
      } else if (bigdataController.kafka) {
        name = dbmRouteRedirect.kafka;
      } else if (bigdataController.pulsar) {
        name = dbmRouteRedirect.pulsar;
      } else if (bigdataController.influxdb) {
        name = dbmRouteRedirect.influxdb;
      }
      dbmRoute.redirect = {
        name,
      };
    }

    renderRoutes.push(route);
  }

  return renderRoutes;
}
