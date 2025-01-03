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

import { TicketTypes } from '@common/const';

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

import type { DetailBase } from './details/common';

export type * as Doris from './details/doris';
export type * as Dumper from './details/dumper';
export type * as Es from './details/elastic-search';
export type * as Hdfs from './details/hdfs';
export type * as Influxdb from './details/influxdb';
export type * as Kafka from './details/kafka';
export type * as Mongodb from './details/mongodb';
export type * as Mysql from './details/mysql/index';
export type * as Pulsar from './details/pulsar';
export type * as Redis from './details/redis/index';
export type * as Riak from './details/riak';
export type * as Sqlserver from './details/sqlserver';
export type * as TendbCluster from './details/tendbCluster';

const STATUS_APPROVE = 'APPROVE';
const STATUS_FAILED = 'FAILED';
const STATUS_RESOURCE_REPLENISH = 'RESOURCE_REPLENISH';
const STATUS_SUCCEEDED = 'SUCCEEDED';
const STATUS_RUNNING = 'RUNNING';
const STATUS_TERMINATED = 'TERMINATED';
const STATUS_TIMER = 'TIMER';
const STATUS_TODO = 'TODO';
const STATUS_INNER_TODO = 'INNER_TODO';

export default class Ticket<T extends unknown | DetailBase = unknown> {
  static STATUS_APPROVE = STATUS_APPROVE;
  static STATUS_FAILED = STATUS_FAILED;
  static STATUS_RESOURCE_REPLENISH = STATUS_RESOURCE_REPLENISH;
  static STATUS_SUCCEEDED = STATUS_SUCCEEDED;
  static STATUS_RUNNING = STATUS_RUNNING;
  static STATUS_TERMINATED = STATUS_TERMINATED;
  static STATUS_TIMER = STATUS_TIMER;
  static STATUS_TODO = STATUS_TODO;
  static STATUS_INNER_TODO = STATUS_INNER_TODO;

  static statusTextMap = {
    [STATUS_APPROVE]: t('待审批'),
    [STATUS_TODO]: t('待执行'),
    [STATUS_RUNNING]: t('执行中'),
    [STATUS_RESOURCE_REPLENISH]: t('待补货'),
    [STATUS_INNER_TODO]: t('待继续'),
    [STATUS_FAILED]: t('已失败'),
    [STATUS_SUCCEEDED]: t('已完成'),
    [STATUS_TERMINATED]: t('已终止'),
    [STATUS_TIMER]: t('定时中'),
  };

  bk_biz_id: number;
  bk_biz_name: string;
  cost_time: number;
  create_at: string;
  creator: string;
  db_app_abbr: string;
  details: T;
  group: string;
  id: number;
  ignore_duplication: boolean;
  is_reviewed: boolean;
  permission: {
    ticket_view: boolean;
  };
  related_object: {
    title: string;
    objects: string[];
  };
  remark: string;
  send_msg_config: Record<string, string>;
  status: keyof typeof Ticket.statusTextMap;
  status_display: string;
  ticket_type: TicketTypes;
  ticket_type_display: string;
  todo_helpers: string[];
  todo_operators: string[];
  update_at: string;
  updater: string;

  constructor(payload = {} as Ticket<T>) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.cost_time = payload.cost_time;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_app_abbr = payload.db_app_abbr;
    this.details = payload.details;
    this.group = payload.group;
    this.id = payload.id;
    this.ignore_duplication = payload.ignore_duplication;
    this.is_reviewed = payload.is_reviewed;
    this.permission = payload.permission || {};
    this.remark = payload.remark;
    this.send_msg_config = payload.send_msg_config || {};
    this.status = payload.status;
    this.status_display = payload.status_display;
    this.ticket_type = payload.ticket_type;
    this.ticket_type_display = payload.ticket_type_display;
    this.todo_helpers = payload.todo_helpers || [];
    this.todo_operators = payload.todo_operators || [];
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.related_object = payload.related_object || {
      objects: [],
      title: '',
    };
  }

  get statusText() {
    return Ticket.statusTextMap[this.status];
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get isTodo() {
    return [
      Ticket.STATUS_APPROVE,
      Ticket.STATUS_TODO,
      Ticket.STATUS_RESOURCE_REPLENISH,
      Ticket.STATUS_FAILED,
      Ticket.STATUS_RUNNING,
    ].includes(this.status);
  }

  get isFinished() {
    return [Ticket.STATUS_SUCCEEDED, Ticket.STATUS_TERMINATED].includes(this.status);
  }
}
