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

// eslint-disable-next-line simple-import-sort/imports
import { createApp } from 'vue';
import bkuiVue from 'bkui-vue';
import dayjs from 'dayjs';
import tz from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import duration from 'dayjs/plugin/duration';
import { createPinia } from 'pinia';

import { useFunController, useGlobalBizs, useSystemEnviron } from '@stores';

import { setGlobalComps } from '@common/importComps';

import i18n from '@locales/index';
import BkTrace from '@blueking/bk-trace-core';

import App from './App.vue';
import getRouter from './router';
import SubApp from './SubApp.vue';

import '@blueking/ip-selector/dist/styles/vue2.6.x.css';
import '@lib/bk-icon/iconcool';
import '@styles/common.less';
import 'bkui-vue/dist/style.css';
import '@xterm/xterm/css/xterm.css';
import { setGlobalDirectives } from '@/directives/index';
import { subEnv } from '@blueking/sub-saas';

import('tippy.js/dist/tippy.css');
import('tippy.js/themes/light.css');

dayjs.extend(utc);
dayjs.extend(tz);
dayjs.extend(duration);

window.changeConfirm = false;

const app = createApp(subEnv ? SubApp : App);
// 自定义全局组件
setGlobalComps(app);
const piniaInstance = createPinia();
app.use(piniaInstance);
// 注册全局指令
setGlobalDirectives(app);

app.use(bkuiVue);
app.use(i18n);

window.BKApp = app;

const { fetchFunController } = useFunController();
const { fetchBizs } = useGlobalBizs();
const systemEnvironStore = useSystemEnviron();

Promise.all([fetchFunController(), fetchBizs(), systemEnvironStore.fetchSystemEnviron()]).then(() => {
  app.use(getRouter());
  const { urls } = systemEnvironStore;
  const reportUrl = urls.BKDATA_FRONTEND_REPORT_URL;
  if (reportUrl) {
    // 监控数据上报
    app.use(BkTrace, {
      appCode: urls.APP_CODE, // APP名称
      appVersion: urls.APP_VERSION, // APP版本
      spaceID: 'dbm', // 当前空间
      spaceType: 'project', // 当前空间类型
      url: reportUrl, // 上报地址
    });
  }

  app.mount('#app');
});

/**
 * 浏览器框口关闭提醒
 */
window.addEventListener('beforeunload', (event) => {
  // 需要做 Boolean 类型的值判断
  if (window.changeConfirm !== true) {
    return null;
  }
  const e = event || window.event;
  if (e) {
    e.returnValue = '离开将会导致未保存信息丢失';
  }
  return '离开将会导致未保存信息丢失';
});
