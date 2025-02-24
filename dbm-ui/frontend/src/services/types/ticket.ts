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
import { type Mysql } from '@services/model/ticket/ticket';

/**
 * 单据流程信息
 */
export interface FlowItem {
  context: {
    expire_time?: number;
  };
  cost_time: number;
  details: {
    operators?: string[]; // 系统单据处理人才会有这个
    ticket_data: Mysql.ImportSqlFile;
  };
  end_time: string;
  err_code: number;
  err_msg: string;
  flow_expire_time?: number;
  flow_obj_id: string;
  flow_type: string;
  flow_type_display: string;
  id: number;
  start_time: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'SKIPPED' | 'REVOKED' | 'TERMINATED';
  summary: string;
  ticket: number;
  todos: FlowItemTodo[];
  update_at: string;
  url: string;
}

/**
 * 单据流程待办信息
 */
export interface FlowItemTodo {
  context: {
    administrators?: string[];
    flow_id: number;
    node_id: string;
    ticket_id: number;
    user?: string;
  };
  cost_time: number;
  done_at: null | string;
  done_by: string;
  flow: number;
  flow_id: number;
  id: number;
  name: string;
  operators: string[];
  status: 'TODO' | 'RUNNING' | 'DONE_SUCCESS' | 'DONE_FAILED';
  ticket: number;
  ticket_id: number;
  type: 'APPROVE' | 'INNER_APPROVE' | 'RESOURCE_REPLENISH';
  url: string;
}
