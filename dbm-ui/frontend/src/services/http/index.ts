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

import axios, { AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios';
import { Message } from 'bkui-vue';

import type { Permission } from '@services/types/common';

interface LoginData {
  width: number,
  height: number,
  login_url: string
}

type Methods = 'delete' | 'get' | 'head' | 'options' | 'post' | 'put' | 'patch';
interface ResolveResponseParams<D> {
  response: AxiosResponse<D, any>,
  config: Record<string, any>,
}
interface Config extends AxiosRequestConfig {
  globalError?: boolean
}
interface ServiceResponseData<T> {
  code: number,
  message: string,
  request_id: string,
  data: T
}
type HttpMethod = <T>(url: string, payload?: any, useConfig?: Config) => Promise<T>;
interface Http {
  get: HttpMethod,
  delete: HttpMethod,
  head: HttpMethod,
  options: HttpMethod,
  post: HttpMethod,
  put: HttpMethod,
  patch: HttpMethod,
}
enum STATUS_CODE {
  SUCCESS = 0,
  PERMISSION = 9900403,
  UNAUTHORIZED = 401
}

const baseURL = /http(s)?:\/\//.test(window.PROJECT_ENV.VITE_AJAX_URL_PREFIX)
  ? window.PROJECT_ENV.VITE_AJAX_URL_PREFIX
  : location.origin + window.PROJECT_ENV.VITE_AJAX_URL_PREFIX;

const methodsWithoutData = ['get', 'head', 'options'];
const methodsWithData = ['post', 'put', 'delete', 'patch'];
const methods = [...methodsWithoutData, ...methodsWithData];

const http = {};

const initConfig = (useConfig: Config) => {
  const baseConfig = {
    globalError: true,
  };
  return Object.assign(baseConfig, useConfig) as Config;
};


const handleResponse = <T>({
  response,
}: ResolveResponseParams<ServiceResponseData<T>>) => {
  const { data } = response;

  if (data.code === STATUS_CODE.PERMISSION) {
    !window.permission.isShow && window.permission.show(data.data as unknown as Permission);
    return Promise.reject(data);
  }

  if (data.code !== STATUS_CODE.SUCCESS) {
    return Promise.reject(data);
  }

  return Promise.resolve(data.data);
};

const handleReject = (error: AxiosError, config: Record<string, any>) => {
  const {
    message,
    response,
  } = error;

  const data = response?.data;
  const code = response?.status;

  if (Number(code) === STATUS_CODE.UNAUTHORIZED) {
    const loginData = data as LoginData;
    const { VITE_PUBLIC_PATH } = window.PROJECT_ENV;
    const src = loginData?.login_url
      ? `${loginData.login_url}?size=big&c_url=${window.location.origin}${VITE_PUBLIC_PATH ? VITE_PUBLIC_PATH : '/'}login_success.html?is_ajax=1`
      : '';

    src && window.login.showLogin({
      src,
      width: loginData.width,
      height: loginData.height,
    });

    return;
  }

  // 全局捕获错误给出提示
  if (config.globalError) {
    Message({ theme: 'error', message });
  }

  return Promise.reject(error);
};

methods.forEach((method) => {
  Object.defineProperty(http, method, {
    get() {
      return <T>(url: string, payload: any = {}, useConfig = {}) => {
        const config = initConfig(useConfig);

        const params = {
          ...useConfig,
        };
        if (methodsWithData.includes(method)) {
          Object.assign(params, {
            data: payload,
          });
        } else {
          Object.assign(params, {
            params: payload,
          });
        }
        return axios({
          baseURL,
          url,
          method,
          withCredentials: true,
          xsrfCookieName: 'dbm_csrftoken',
          xsrfHeaderName: 'X-CSRFToken',
          headers: {
            'x-requested-with': 'XMLHttpRequest',
          },
          ...params,
        })
          .then(response => handleResponse<T>({
            response,
            config,
          }))
          .catch(error => handleReject(error, config));
      };
    },
  });
});

export default http as Http;
