/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited; a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing; software distributed under the License is distributed
 * on an "AS IS" BASIS; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND; either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import dayjs from 'dayjs';

import { utcDisplayTime } from '@utils';

export interface IResourceTag {
  tag: string;
  boundIp: string[];
  creator: string;
  creationTime: string;
  id: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export default class ResourceTagModel {
  tag: string;
  boundIp: string[];
  creator: string;
  creationTime: string;
  id: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  is_show_edit: boolean;

  constructor(payload: IResourceTag) {
    this.id = payload.id;
    this.tag = payload.tag;
    this.boundIp = payload.boundIp;
    this.creator = payload.creator;
    this.creationTime = payload.creationTime;
    this.is_enabled = payload.is_enabled;
    this.created_at = payload.created_at;
    this.updated_at = payload.updated_at;
    this.is_show_edit = false;
  }

  get isNewCreated() {
    return dayjs().isBefore(dayjs(this.created_at).add(24, 'hour'));
  }

  get creationTimeDisplay() {
    return utcDisplayTime(this.creationTime);
  }

  get updatedAtDisplay() {
    return utcDisplayTime(this.updated_at);
  }

  get ipCount() {
    return this.boundIp.length;
  }

  generateStatus() {
    return this.is_enabled ? 'ACTIVE' : 'TERMINATED'; // 根据 is_enabled 返回状态
  }
}
