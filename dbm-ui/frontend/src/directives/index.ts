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

import * as directives from 'bkui-vue/lib/directives';
import type { App } from 'vue';

import Cursor from './cursor';
import OverflowTips from './overflowTips';

type BkuiDirectives = keyof typeof directives;

/**
 * 设置全局指令
 * @param app vue app
 */
export const setGlobalDirectives = (app: App<Element>) => {
  // 注册 bkui-vue 指令
  Object.keys(directives).forEach((key: string) => {
    app.directive(key, directives[key as BkuiDirectives]);
  });

  // 自定义指令
  app.directive('overflow-tips', OverflowTips);
  app.directive('cursor', Cursor);
};
