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

// eslint-disable-next-line spaced-comment
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly MODE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
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

declare module 'vite-plugin-monaco-editor' {
  interface MonacoEditorOptions {
    // 根据实际插件文档填写选项
    language?: string;
    theme?: string;
    // 其他可能的选项...
  }

  const monacoEditorPlugin: (options: MonacoEditorOptions) => any;

  export default {
    default: monacoEditorPlugin,
  };
}

declare module 'js-cookie';
declare module '@blueking/app-select';
declare module '@blueking/notice-component';
declare module '@blueking/login-modal' {
  export function showLoginModal(params: { loginUrl: string }): void;
}
declare module '@blueking/sub-saas';

declare module '@blueking/sub-saas' {
  export function connectToMain(router: Router): any;
  export const rootPath: string;
  export const subEnv: boolean;
}

interface URLSearchParams {
  keys(): string[];
}

type ValueOf<T> = T[keyof T];

type ServiceReturnType<T extends (...args: any) => Promise<any>> = T extends (...args: any) => Promise<infer R>
  ? R
  : any;

type ServiceParameters<T extends (params: any) => Promise<any>> = Parameters<T>[length] extends 0
  ? never
  : Parameters<T>[0];

type KeyExpand<T> = {
  [K in keyof T]: T[K];
};

type LeftIsExtendsRightReturnValue<L, R, V> = L extends R ? never : V;

declare interface Window {
  changeConfirm: boolean | 'popover';
  clipboardData: {
    getData: (params: string) => string;
  };
  PROJECT_ENV: {
    VITE_PUBLIC_PATH: string;
    VITE_AJAX_URL_PREFIX: string;
    VITE_ROUTER_PERFIX: string;
  };
  PROJECT_CONFIG: {
    BIZ_ID: number;
    TICKET_DETAIL_REQUEST_CONTROLLER: AbortController;
  };
  BKApp: App<Element>;
}
