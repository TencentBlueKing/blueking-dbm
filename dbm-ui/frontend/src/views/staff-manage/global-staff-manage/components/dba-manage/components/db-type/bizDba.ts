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
import DBAdminModel from '@services/model/db-admin/db-admin';
import ResourceTagModel from '@services/model/db-resource/ResourceTag';
import type { BizItem } from '@services/types';

import { utcDisplayTime } from '@utils';

export default class BizDba implements BizItem, DBAdminModel {
  bk_biz_id: number;
  db_type: string;
  db_type_display: string;
  display_name: string;
  english_name: string;
  is_edit: boolean;
  is_show: boolean;
  level2_dba: string[];
  level2_dba_edit: string[];
  managed_time: string;
  name: string;
  permission: DBAdminModel['permission'];
  pinyin_head: string;
  pinyin_name: string;
  primary_dba: string;
  primary_dba_edit: string[];
  standby_dba: string;
  standby_dba_edit: string[];
  status: 'managed' | 'unmanaged'; // managed 已纳管 ; unmanaged 未纳管
  tags: ResourceTagModel[];
  update_at: string;
  updater: string;
  users: string[];

  constructor(payload = {} as BizDba) {
    this.bk_biz_id = payload.bk_biz_id;
    this.db_type = payload.db_type;
    this.db_type_display = payload.db_type_display;
    this.display_name = payload.display_name;
    this.english_name = payload.english_name;
    this.is_edit = payload.is_edit;
    this.is_show = payload.is_show;
    this.level2_dba = payload.level2_dba;
    this.level2_dba_edit = payload.level2_dba_edit;
    this.managed_time = payload.managed_time;
    this.name = payload.name;
    this.permission = payload.permission || {};
    this.pinyin_head = payload.pinyin_head;
    this.pinyin_name = payload.pinyin_name;
    this.primary_dba = payload.primary_dba;
    this.primary_dba_edit = payload.primary_dba_edit;
    this.standby_dba = payload.standby_dba;
    this.standby_dba_edit = payload.standby_dba_edit;
    this.status = payload.status;
    this.tags = payload.tags;
    this.users = payload.users;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get isAssigned() {
    return [this.primary_dba, this.standby_dba, ...this.level2_dba].filter((item) => item).length > 0;
  }

  get managedTimeDisplay() {
    return utcDisplayTime(this.managed_time);
  }

  get updateAtTime() {
    return utcDisplayTime(this.update_at);
  }
}
