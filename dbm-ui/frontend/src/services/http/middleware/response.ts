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
  AxiosError,
  AxiosInterceptorManager,
  AxiosResponse,
} from 'axios';

import IamApplyDataModel from '@services/model/iam/apply-data';

import { useEventBus } from '@hooks';

import {
  loginDialog,
  messageError,
  parseURL,
  permissionDialog,
} from '@utils';

import RequestError from '../lib/request-error';


// 标记已经登录过状态
// 第一次登录跳转登录页面，之后弹框登录
let hasLogined = false;

const redirectLogin = (loginUrl:string) => {
  const { protocol, host } = parseURL(loginUrl);
  const domain = `${protocol}://${host}`;

  if (hasLogined) {
    loginDialog(`${domain}/login/plain/?c_url=${decodeURIComponent(`${window.location.origin}${window.PROJECT_ENV.VITE_PUBLIC_PATH}login-success.html`)}`);
  } else {
    window.location.href = `${domain}/login/?c_url=${decodeURIComponent(window.location.href)}`;
  }
};

export default (interceptors: AxiosInterceptorManager<AxiosResponse>) => {
  interceptors.use((response: AxiosResponse) => {
    // 处理http响应成功，后端返回逻辑
    switch (response.data.code) {
      // 后端业务逻辑处理成功
      case 0:
        hasLogined = true;
        return response.data;
      default: {
        // 后端逻辑处理报错
        const { code, message = '系统错误' } = response.data;
        throw new RequestError(code, message, response);
      }
    }
  }, (error: AxiosError<{message: string}> & {__CANCEL__: any}) => {
    // 超时取消
    if (error.__CANCEL__) { // eslint-disable-line no-underscore-dangle
      return Promise.reject(new RequestError('CANCEL', '请求已取消'));
    }
    // 处理 http 错误响应逻辑
    if (error.response) {
      // 登录状态失效
      if (error.response.status === 401) {
        return Promise.reject(new RequestError(401, '登录状态失效', error.response));
      }
      // 默认使用 http 错误描述，
      // 如果 response body 里面有自定义错误描述优先使用
      let errorMessage = error.response.statusText;
      if (error.response.data && error.response.data.message) {
        errorMessage = error.response.data.message as string;
      }
      return Promise.reject(new RequestError(
        error.response.status || -1,
        errorMessage,
        error.response,
      ));
    }
    return Promise.reject(new RequestError(-1, `${window.PROJECT_ENV.VITE_AJAX_URL_PREFIX} 无法访问`));
  });

  // 统一错误处理逻辑
  interceptors.use(undefined, (error: RequestError) => {
    switch (error.code) {
      // 未登陆
      case 401:
        redirectLogin(error.response.data.login_url);
        break;
      case 403:
        handlePermission(error);
        break;
      case 'CANCEL':
        break;
        // 网络超时
      case 'ECONNABORTED':
        messageError('请求超时');
        break;
      default:
        if (error.response.data.code === 9900403) {
          handlePermission(error);
        } else {
          messageError(`${error.message} (${error.response.data.trace_id})`);
        }
    }
    return Promise.reject(error);
  });
};

const handlePermission = (error:RequestError) => {
  const {  emit } = useEventBus();
  // eslint-disable-next-line no-case-declarations
  const requestPayload = error.response.config.payload;
  // eslint-disable-next-line no-case-declarations
  const iamResult = new IamApplyDataModel(error.response.data.data || {});
  if (requestPayload.permission === 'page') {
    // 配合 jb-router-view（@components/audit-router-view）全局展示没权限提示
    emit('permission-page', iamResult);
  } else if (requestPayload.permission === 'catch') {
    // 配合 apply-section （@components/apply-permission/catch）使用，局部展示没权限提示
    emit('permission-catch', iamResult);
  } else {
    // 弹框展示没权限提示
    permissionDialog(iamResult);
  }
};
