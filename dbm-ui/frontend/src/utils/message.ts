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

import { Message } from 'bkui-vue';

export const messageSuccess = (message: string, delay = 3000) => {
  Message({
    message,
    theme: 'success',
    delay,
  });
};

export const messageError = (message: string, delay = 3000) => {
  Message({
    message,
    theme: 'error',
    delay,
  });
};

export const messageWarn = (message: string, delay = 3000) => {
  Message({
    message,
    theme: 'warning',
    delay,
  });
};
