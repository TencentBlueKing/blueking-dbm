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

import bkuiVue from 'bkui-vue';
import { createPinia } from 'pinia';
import { createApp, markRaw } from 'vue';

import { useSystemEnviron } from '@stores';

import { setGlobalComps } from '@common/importComps';

import App from './App.vue';
import i18n from './locales/index';
import getRouter from './router';

import '@blueking/ip-selector/dist/styles/vue2.6.x.css';
import 'bkui-vue/dist/style.css';
import '@styles/common.less';
import '@public/bk-icon/iconcool';
import { setGlobalDirectives } from '@/directives/index';
import('tippy.js/dist/tippy.css');
import('tippy.js/themes/light.css');

window.changeConfirm = false;

(async function () {
  const app = createApp(App);
  const router = await getRouter();

  // 自定义全局组件
  setGlobalComps(app);

  // 注册全局指令
  setGlobalDirectives(app);

  const piniaInstance = createPinia();
  piniaInstance.use(({ store }) => {
    // eslint-disable-next-line no-param-reassign
    store.router = markRaw(router);
  });
  app.use(piniaInstance);
  app.use(bkuiVue);
  app.use(i18n);
  app.use(router);

  app.mount('#app');

  /**
   * 获取环境变量
   */
  const systemEnvironStore = useSystemEnviron();
  systemEnvironStore.fetchSystemEnviron();
}());

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
  // 如果是通过登录触发提示，则关闭登录 dialog
  if (window.login.isShow) {
    window.login.hideLogin();
  }
  return '离开将会导致未保存信息丢失';
});
