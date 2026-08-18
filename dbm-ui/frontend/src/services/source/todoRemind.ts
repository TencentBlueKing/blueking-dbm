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

import http, { type IRequestPayload } from '../http';

const path = '/apis/conf/todo_remind';

interface TodoRemindParams {
  is_enable: boolean;
  notice: {
    type: string;
    value: string;
  }[];
  remind_time: {
    day_of_week?: string;
    hour: string;
    minute: string;
  };
}

/**
 * 获取每日待办提醒
 */
export const getTodoRemind = function (payload = {} as IRequestPayload) {
  return http.get<TodoRemindParams>(`${path}/get_todo_remind_conf/`, {}, payload);
};

/**
 * 更新每日待办提醒
 */
export const updateTodoRemind = function (params: TodoRemindParams) {
  return http.post(`${path}/update_todo_remind_conf/`, params);
};
