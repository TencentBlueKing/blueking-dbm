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
import relativeTime from 'dayjs/plugin/relativeTime';
import tz from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import duration from 'dayjs/plugin/duration';
import { createPinia } from 'pinia';
import BkUserDisplayName from '@blueking/bk-user-display-name';

import { useFunController, useGlobalBizs, useSystemEnviron, useUserProfile } from '@stores';

import { setGlobalComps } from '@common/importComps';

import i18n from '@locales/index';
import BkTrace from '@blueking/bk-trace-core';
import { BkXssFilterDirective } from '@blueking/xss-filter';

import App from './App.vue';
import getRouter from './router';
import SubApp from './SubApp.vue';

import '@blueking/ip-selector/dist/styles/vue2.6.x.css';
import '@lib/bk-icon/iconcool';
import '@styles/common.less';
import '@xterm/xterm/css/xterm.css';
import 'bkui-vue/dist/style.variable.css';
import { setGlobalDirectives } from '@/directives/index';
import { subEnv } from '@blueking/sub-saas';
import 'dayjs/locale/zh-cn';

import('tippy.js/dist/tippy.css');
import('tippy.js/themes/light.css');
import('@blueking/date-picker/vue3/vue3.css');

dayjs.extend(utc);
dayjs.extend(tz);
dayjs.extend(duration);
dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

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
app.use(BkXssFilterDirective, {
  defaultOptions: {
    imgSrcMode: 'none',
  },
});

window.BKApp = app;

const { fetchFunController } = useFunController();
const { fetchBizs } = useGlobalBizs();
const systemEnvironStore = useSystemEnviron();
// fetchBizs 内部会先 await fetchProfile，租户 ID 在下面的 then 里才可用
const userProfileStore = useUserProfile();

Promise.all([fetchFunController(), fetchBizs(), systemEnvironStore.fetchSystemEnviron()]).then(() => {
  app.use(getRouter());
  const { urls } = systemEnvironStore;
  const reportUrl = urls.BKDATA_FRONTEND_REPORT_URL;
  window.PROJECT_CONFIG.AI_LOG_ANALYSIS_OPEN = !!urls.BK_AIDEV_LOG_ANALYSIS_URL;
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
  // 包产物是带 __esModule 标记的 CJS，默认导出在不同打包器下可能是 class 本身，也可能是整个 exports 对象
  const BkUserDisplayNameClass =
    (BkUserDisplayName as { default?: typeof BkUserDisplayName } & typeof BkUserDisplayName).default ??
    BkUserDisplayName;
  BkUserDisplayNameClass.configure({
    // 必填，网关地址
    apiBaseUrl: urls.USER_MANAGE_FRONTEND_APIGW_DOMAIN,
    // 可选，缓存时间，单位为毫秒, 默认 5 分钟, 只对单一用户查询有效
    cacheDuration: 1000 * 60 * 5,
    // 可选，当输入为空时，显示的文本，默认为 '--'
    emptyText: '--',
    // 必填，租户 ID，为空时组件库回退成直接展示用户名
    tenantId: userProfileStore.tenantId,
  });

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
