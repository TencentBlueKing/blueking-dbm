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

import type { DBAOperateTypes, DBARoleTypes, DBTypes } from '@common/const';

import { utcDisplayTime } from '@utils';

export default class DBAdminOperationRecord {
  bk_biz_id: number;
  change_after: string;
  change_before: string;
  create_at: string;
  creator: string;
  db_type: DBTypes;
  id: number;
  operate_type: DBAOperateTypes;
  role: DBARoleTypes;

  constructor(payload = {} as DBAdminOperationRecord) {
    this.bk_biz_id = payload.bk_biz_id;
    this.change_after = payload.change_after;
    this.change_before = payload.change_before;
    this.id = payload.id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_type = payload.db_type;
    this.operate_type = payload.operate_type;
    this.role = payload.role;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at) || '--';
  }
}
