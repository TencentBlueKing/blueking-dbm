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

import { useInfo } from '@hooks';

import { t } from '@locales/index';

export const leaveConfirm = () => {
  if (!window.changeConfirm || window.changeConfirm === 'popover') {
    return Promise.resolve(true);
  }

  return new Promise((resolve, reject) => {
    useInfo({
      title: t('确认离开当前页'),
      content: t('离开将会导致未保存信息丢失'),
      confirmTxt: t('离开'),
      onConfirm: () => {
        window.changeConfirm = false;
        resolve(true);
        return true;
      },
      onCancel: () => {
        reject(false);
      },
    });
  });
};
