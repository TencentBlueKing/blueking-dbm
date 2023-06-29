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

import DbConfigureRoutes from '@views/db-configure/routes';
// import deploymentPlanRoutes from '@views/deployment-plan/routes';
import esRoutes from '@views/es-manage/routes';
import eventCenterRouters from '@views/event-center/routes';
import hdfsRoutes from '@views/hdfs-manage/routes';
import InfluxDBRoutes from '@views/influxdb-manage/routes';
import kafkaRoutes from '@views/kafka-manage/routes';
import missionRoutes from '@views/mission/routes';
import mysqlRoutes from '@views/mysql/routes';
import passwordPolicyRoutes from '@views/password-policy/routes';
import pulsarRoutes from '@views/pulsar-manage/routes';
import redisRoutes from '@views/redis/routes';
import resourcePool from '@views/resource-pool/routes';
import resourceSpecRouters from '@views/resource-spec/routes';
import serviceApplyRoutes from '@views/service-apply/routes';
import staffSettingRoutes from '@views/staff-setting/routes';
import ticketsRoutes from '@views/tickets/routes';
import versionFilesRoutes from '@views/version-files/routes';
import whitelistRoutes from '@views/whitelist/routes';

import { MainViewRouteNames, type MainViewRouteNameValues } from '../common/const';

const routes = [
  ...DbConfigureRoutes,
  ...esRoutes,
  ...hdfsRoutes,
  ...kafkaRoutes,
  ...missionRoutes,
  ...mysqlRoutes,
  ...passwordPolicyRoutes,
  ...redisRoutes,
  ...serviceApplyRoutes,
  ...staffSettingRoutes,
  ...ticketsRoutes,
  ...versionFilesRoutes,
  ...whitelistRoutes,
  ...eventCenterRouters,
  ...pulsarRoutes,
  ...InfluxDBRoutes,
  // ...deploymentPlanRoutes,
  ...resourcePool,
  ...resourceSpecRouters,
];

/**
 * 获取主视图下的 children routes
 */
export const getRouteChildren = () => {
  const routeChildrenMap: Record<MainViewRouteNameValues, RouteRecordRaw[]> = {
    [MainViewRouteNames.SelfService]: [],
    [MainViewRouteNames.Database]: [],
    [MainViewRouteNames.Platform]: [],
  };

  for (const route of routes) {
    const { routeParentName } = route.meta || {};

    if (routeParentName && routeChildrenMap[routeParentName as keyof typeof routeChildrenMap]) {
      routeChildrenMap[routeParentName as keyof typeof routeChildrenMap].push(route);
    }
  }

  return routeChildrenMap;
};
