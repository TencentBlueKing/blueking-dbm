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

import _ from 'lodash';
import { isVNode } from 'vue';

import { type InfoOptions, useInfo } from './useInfo';

enum ICON_TYPE {
  success = 'db-icon-check-line',
  danger = 'db-icon-close',
  warnning = 'db-icon-exclamation'
}
type IconTypeString = keyof typeof ICON_TYPE;

interface InfoIconOptions extends InfoOptions {
  type?: IconTypeString,
}

export const useInfoWithIcon = (() => (options: InfoIconOptions) => {
  const { type, extCls } = options;
  if (type && Object.keys(ICON_TYPE).includes(type)) {
    // icon class
    const icon = ICON_TYPE[type];
    // dialog title info
    const title = () => {
      if (isVNode(options.title)) {
        return <title />;
      }
      return _.isFunction(options.title) ? options.title() : options.title;
    };

    return useInfo({
      ...options,
      extCls: ['db-info-with-icon', extCls ?? ''].join(' '),
      title: () => (
        <div class="db-info-with-icon__title">
          <i class={['db-info-with-icon__icon', `db-info-with-icon__icon--${type}`, icon]} />
          <span class="db-info-with-icon__name">{title()}</span>
        </div>
      ),
    });
  }

  return useInfo({ ...options });
})();
