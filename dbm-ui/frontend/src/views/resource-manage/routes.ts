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

import FunctionControllModel from '@services/model/function-controller/functionController';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const resourcePoolRoute = {
  name: 'resourcePool',
  path: 'pool',
  meta: {
    navName: t('DB 资源池'),
  },
  component: () => import('@views/resource-manage/pool/Index.vue'),
}

const resourcePoolOperationRecordRoute = {
  name: 'resourcePoolOperationRecord',
  path: 'record',
  meta: {
    navName: t('资源操作记录'),
  },
  component: () => import('@views/resource-manage/record/Index.vue'),
}

const resourcePoolDirtyMachinesRoute = {
  name: 'resourcePoolDirtyMachines',
  path: 'dirty-machine',
  meta: {
    navName: t('污点主机处理'),
  },
  component: () => import('@views/resource-manage/dirty-machine/Index.vue'),
}

const resourceSpecRoute = {
  name: 'resourceSpec',
  path: 'spec',
  meta: {
    navName: t('资源规格管理'),
    fullscreen: true,
  },
  component: () => import('@views/resource-manage/spec/Index.vue'),
}

const mainRoute = [
  {
    name: 'resourceManage',
    path: 'resource-manage',
    component: () => import('@views/resource-manage/Index.vue'),
    redirect: {
      name: 'resourcePool',
    },
    children: [] as RouteRecordRaw[],
  },
];


export default function getRoutes(funControllerData: FunctionControllModel) {
  let existResourcePool = false;

  if (checkDbConsole(funControllerData, 'resourceManage.resourceSpec')) {
    mainRoute[0].children.push(resourceSpecRoute);
  }

  if (checkDbConsole(funControllerData, 'resourceManage.resourcePool')) {
    mainRoute[0].children.push(resourcePoolRoute);
    existResourcePool = true;
  }

  if (checkDbConsole(funControllerData, 'resourceManage.dirtyHostManage')) {
    mainRoute[0].children.push(resourcePoolDirtyMachinesRoute);
  }

  if (checkDbConsole(funControllerData, 'resourceManage.resourceOperationRecord')) {
    mainRoute[0].children.push(resourcePoolOperationRecordRoute);
  }

  if (mainRoute[0].children.length) {
    if (!existResourcePool) {
      mainRoute[0].redirect.name = mainRoute[0].children[0].name as string;
    }
  } else {
    mainRoute[0].redirect.name = '';
  }

  return mainRoute;
}
