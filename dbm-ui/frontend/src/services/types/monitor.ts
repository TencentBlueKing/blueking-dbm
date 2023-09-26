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

export interface UpdatePolicyParams {
  targets: {
    level: string,
    rule: {
      key: string,
      value: string[],
    },
  }[],
  test_rules: {
    type: string,
    level: number,
    config: [
      {
        method: string,
        threshold: number,
      },
    ][],
    unit_prefix: string,
  }[],
  notify_rules: string[],
  notify_groups: number[],
}

export interface CreateCycleDutyRuleParams {
  name: string,
  priority: number,
  db_type: string,
  category: string,
  effective_time: string,
  end_time: string,
  duty_arranges: {
    duty_number: number,
    duty_day: number,
    members: string[],
    work_type: string,
    work_days: number[],
    work_times: string[],
  }[]
}

export interface CreateCustomDutyRuleParams extends Omit<CreateCycleDutyRuleParams, 'duty_arranges'> {
  duty_arranges: {
    date: string,
    work_times: string[],
    members: string[],
  }[]
}
