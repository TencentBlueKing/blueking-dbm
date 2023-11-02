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

import type {
  RouteLocationNormalizedLoaded,
  Router,
} from 'vue-router';

import { leaveConfirm } from '@utils';


const leaveConfirmHandler = (currentRoute: RouteLocationNormalizedLoaded) => {
  if (typeof currentRoute?.meta?.leaveConfirm === 'function') {
    return currentRoute.meta.leaveConfirm();
  }
  return leaveConfirm();
};

let lastRouterHrefCache = '';

/**
 * 路由切换时
 * 检测页面数据的编辑状态——弹出确认框提示用户确认
 * @param router router 实例
 */
export const routerInterceptor = (router: Router) => {
  router.beforeEach(async (to, from, next) => {
    await leaveConfirmHandler(from);
    lastRouterHrefCache = to.fullPath;
    next();
  });

  router.onError((error: any) => {
    if (/Failed to fetch dynamically imported module/.test(error.message)) {
      // window.location.href = lastRouterHrefCache;
    }
  });

  // router.push = (params: Params, callback = () => {}) => {
  //   const { currentRoute } = router;
  //   return leaveConfirmHandler(currentRoute.value).then(
  //     () => {
  //       push(params);
  //     },
  //     () => {
  //       callback();
  //     },
  //   );
  // };

  // router.replace = (params: Params, callback = () => {}) => {
  //   const { currentRoute } = router;
  //   return leaveConfirmHandler(currentRoute.value).then(
  //     () => {
  //       replace(params);
  //     },
  //     () => {
  //       callback();
  //     },
  //   );
  // };

  // router.go = (delta: number) => {
  //   const { currentRoute } = router;
  //   return leaveConfirmHandler(currentRoute.value).then(() => {
  //     go(delta);
  //   });
  // };
};
