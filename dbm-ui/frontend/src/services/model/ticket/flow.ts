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

import { utcDisplayTime } from '@utils';

const TYPE_BK_ITSM = 'BK_ITSM';
const TYPE_INNER_FLOW = 'INNER_FLOW';
const TYPE_PAUSE = 'PAUSE';
const TYPE_DELIVERY = 'DELIVERY';
const TYPE_DESCRIBE_TASK = 'DESCRIBE_TASK';
const TYPE_TIMER = 'TIMER';
const TYPE_RESOURCE_APPLY = 'RESOURCE_APPLY';
const TYPE_RESOURCE_DELIVERY = 'RESOURCE_DELIVERY';
const TYPE_RESOURCE_BATCH_APPLY = 'RESOURCE_BATCH_APPLY';
const TYPE_RESOURCE_BATCH_DELIVERY = 'RESOURCE_BATCH_DELIVERY';
const TYPE_HOST_RECYCLE = 'HOST_RECYCLE';
const TYPE_HOST_IMPORT_RESOURCE = 'HOST_IMPORT_RESOURCE';

const STATUS_PENDING = 'PENDING';
const STATUS_RUNNING = 'RUNNING';
const STATUS_SUCCEEDED = 'SUCCEEDED';
const STATUS_TERMINATED = 'TERMINATED';
const STATUS_FAILED = 'FAILED';
const STATUS_REVOKED = 'REVOKED';
const STATUS_SKIPPED = 'SKIPPED';

const TODO_TYPE_ITSM = 'ITSM';
const TODO_TYPE_APPROVE = 'APPROVE';
const TODO_TYPE_INNER_FAILED = 'INNER_FAILED';
const TODO_TYPE_INNER_APPROVE = 'INNER_APPROVE';
const TODO_TYPE_RESOURCE_REPLENISH = 'RESOURCE_REPLENISH';

const TODO_STATUS_TODO = 'TODO';
const TODO_STATUS_RUNNING = 'RUNNING';
const TODO_STATUS_DONE_SUCCESS = 'DONE_SUCCESS';
const TODO_STATUS_DONE_FAILED = 'DONE_FAILED';

export default class Flow<D = unknown, S = string> {
  static TYPE_BK_ITSM = TYPE_BK_ITSM;
  static TYPE_INNER_FLOW = TYPE_INNER_FLOW;
  static TYPE_PAUSE = TYPE_PAUSE;
  static TYPE_DELIVERY = TYPE_DELIVERY;
  static TYPE_DESCRIBE_TASK = TYPE_DESCRIBE_TASK;
  static TYPE_TIMER = TYPE_TIMER;
  static TYPE_RESOURCE_APPLY = TYPE_RESOURCE_APPLY;
  static TYPE_RESOURCE_DELIVERY = TYPE_RESOURCE_DELIVERY;
  static TYPE_RESOURCE_BATCH_APPLY = TYPE_RESOURCE_BATCH_APPLY;
  static TYPE_RESOURCE_BATCH_DELIVERY = TYPE_RESOURCE_BATCH_DELIVERY;
  static TYPE_HOST_RECYCLE = TYPE_HOST_RECYCLE;
  static TYPE_HOST_IMPORT_RESOURCE = TYPE_HOST_IMPORT_RESOURCE;

  static STATUS_PENDING = STATUS_PENDING;
  static STATUS_RUNNING = STATUS_RUNNING;
  static STATUS_SUCCEEDED = STATUS_SUCCEEDED;
  static STATUS_TERMINATED = STATUS_TERMINATED;
  static STATUS_FAILED = STATUS_FAILED;
  static STATUS_REVOKED = STATUS_REVOKED;
  static STATUS_SKIPPED = STATUS_SKIPPED;

  static TODO_TYPE_ITSM = TODO_TYPE_ITSM;
  static TODO_TYPE_APPROVE = TODO_TYPE_APPROVE;
  static TODO_TYPE_INNER_FAILED = TODO_TYPE_INNER_FAILED;
  static TODO_TYPE_INNER_APPROVE = TODO_TYPE_INNER_APPROVE;
  static TODO_TYPE_RESOURCE_REPLENISH = TODO_TYPE_RESOURCE_REPLENISH;

  static TODO_STATUS_TODO = TODO_STATUS_TODO;
  static TODO_STATUS_RUNNING = TODO_STATUS_RUNNING;
  static TODO_STATUS_DONE_SUCCESS = TODO_STATUS_DONE_SUCCESS;
  static TODO_STATUS_DONE_FAILED = TODO_STATUS_DONE_FAILED;

  context: Record<string, any>;
  cost_time: number;
  create_at: string;
  details: D;
  end_time: string;
  err_code: number;
  err_msg: string;
  flow_alias: string;
  flow_obj_id: string;
  flow_output: Record<string, any>;
  flow_type: string;
  flow_type_display: string;
  id: number;
  retry_type: string;
  start_time: string;
  status: string;
  summary: S;
  ticket: number;
  ticket_type: string;
  todos: {
    context: {
      flow_id: number;
      remark: string;
      ticket_id: number;
    };
    cost_time: number;
    done_at: string;
    done_by: string;
    flow: number;
    id: number;
    name: string;
    operators: string[];
    status: string;
    ticket: number;
    type: string;
  }[];
  update_at: string;
  url: string;

  constructor(payload = {} as Flow<D, S>) {
    this.context = payload.context;
    this.cost_time = payload.cost_time;
    this.create_at = payload.create_at;
    this.details = payload.details;
    this.end_time = payload.end_time;
    this.err_code = payload.err_code;
    this.err_msg = payload.err_msg;
    this.flow_alias = payload.flow_alias;
    this.flow_obj_id = payload.flow_obj_id;
    this.flow_output = payload.flow_output;
    this.flow_type = payload.flow_type;
    this.flow_type_display = payload.flow_type_display;
    this.id = payload.id;
    this.retry_type = payload.retry_type;
    this.start_time = payload.start_time;
    this.status = payload.status;
    this.summary = payload.summary;
    this.ticket = payload.ticket;
    this.ticket_type = payload.ticket_type;
    this.todos = payload.todos || [];
    this.update_at = payload.update_at;
    this.url = payload.url;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
