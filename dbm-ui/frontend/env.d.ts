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

// / <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AJAX_URL_PREFIX: string
  readonly DEV_DOMAIN: string
  readonly MODE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
  readonly hot: any
}

declare module '*.png' {
  const css: string;
  export default png;
}

declare module '*.js' {
  const css: string;
  export default js;
}

declare module '*.css' {
  const css: string;
  export default css;
}

declare interface Window {
  changeConfirm: boolean | 'popover';
  clipboardData: {
    getData: (params: string) => string
  },
  PROJECT_ENV: {
    VITE_PUBLIC_PATH: string,
    VITE_AJAX_URL_PREFIX: string,
    VITE_ROUTER_PERFIX: string,
  },
  PROJECT_CONFIG: {
    BIZ_ID: number
  }
}

declare module 'js-cookie'

interface URLSearchParams {
  keys(): string[];
}

type ValueOf<T> = T[keyof T];

type ServiceReturnType<T extends (...args: any) => Promise<any>> = T extends (...args: any) => Promise<infer R>
? R : any

type ServiceParameters<T extends (params: any) => Promise<any>> = Parameters<T>[length] extends 0
? never : Parameters<T>[0]

type KeyExpand<T> = {
  [K in keyof T]: T[K];
};

type LeftIsExtendsRightReturnValue<L, R, V> = L extends R ? never : V
