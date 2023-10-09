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

import http from './http';
import type { EventSwitchLogItem, EventSwtichItem } from './types/eventSwitch';

// DBHA 切换事件列表
export const getEventSwitchList = function (params: Record<string, any>) {
  return http.get<EventSwtichItem[]>('/apis/event/dbha/ls/', params);
};

// DBHA 切换事件日志
export const getEventSwitchLog = function (params: Record<string, any> & { sw_id: number }) {
  return http.get<EventSwitchLogItem[]>('/apis/event/dbha/cat/', params);
};
