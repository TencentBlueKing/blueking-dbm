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

import type { App } from 'vue';
import { Translation } from 'vue-i18n';

import AuthComponent from '@components/auth/AuthComponent';
import DbCard from '@components/db-card/index.vue';
import DbForm from '@components/db-form/index.vue';
import DbFormItem from '@components/db-form/item.vue';
import DbIcon from '@components/db-icon';
import DbPopconfirm from '@components/db-popconfirm/index.vue';
import DbSearchSelect from '@components/db-search-select/index.vue';
import DbSideslider from '@components/db-sideslider/index.vue';
import DbStatus from '@components/db-status/index.vue';
import DbTable from '@components/db-table/index.vue';
import DbOriginalTable from '@components/db-table/OriginalTable.vue';
import DbTextarea from '@components/db-textarea/DbTextarea.vue';
import FunController from '@components/function-controller/FunController.vue';
import MoreActionExtend from '@components/more-action-extend/Index.vue';
import SmartAction from '@components/smart-action/index.vue';
import { ipSelector } from '@components/vue2/ip-selector';

import UserSelector from '@patch/user-selector/selector.vue';

export const setGlobalComps = (app: App<Element>) => {
  app.component('DbCard', DbCard);
  app.component('DbForm', DbForm);
  app.component('DbFormItem', DbFormItem);
  app.component('DbIcon', DbIcon);
  app.component('DbPopconfirm', DbPopconfirm);
  app.component('DbSearchSelect', DbSearchSelect);
  app.component('DbSideslider', DbSideslider);
  app.component('DbTextarea', DbTextarea);
  app.component('DbTable', DbTable);
  app.component('DbStatus', DbStatus);
  app.component('DbOriginalTable', DbOriginalTable);
  app.component('SmartAction', SmartAction);
  app.component('BkIpSelector', ipSelector);
  app.component('AuthComponent', AuthComponent);
  app.component('I18nT', Translation);
  app.component('FunController', FunController);
  app.component('MoreActionExtend', MoreActionExtend);
  app.component('UserSelector', UserSelector);
};
