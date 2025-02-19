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

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const staffManageRoute = {
  component: () => import('@views/staff-manage/Index.vue'),
  meta: {
    fullScreen: true,
    navName: t('DBA人员管理'),
  },
  name: 'StaffManage',
  path: 'staff-manage',
};

const platformStaffManageRoute = {
  component: () => import('@views/staff-manage/Index.vue'),
  meta: {
    navName: t('DBA人员管理'),
  },
  name: 'PlatformStaffManage',
  path: 'platform-staff-manage',
};

export default function getRoutes() {
  const routes: RouteRecordRaw[] = [];

  if (checkDbConsole('globalConfigManage.staffManage')) {
    routes.push(platformStaffManageRoute);
  }

  if (checkDbConsole('bizConfigManage.StaffManage')) {
    routes.push(staffManageRoute);
  }

  return routes;
}
