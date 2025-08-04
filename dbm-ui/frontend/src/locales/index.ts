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

import Cookies from 'js-cookie';
import { createI18n } from 'vue-i18n';

import en from './en.json';
import cn from './zh-cn.json';

let localeLanguage = 'zh-cn';
const bluekingLanguage = Cookies.get('blueking_language');
if (bluekingLanguage && bluekingLanguage.toLowerCase() === 'en') {
  localeLanguage = 'en';
}
const i18n = createI18n({
  legacy: false,
  locale: localeLanguage,
  messages: {
    en,
    'zh-cn': cn,
  },
  silentTranslationWarn: true,
});

export const { locale, t } = i18n.global;

export default i18n;
