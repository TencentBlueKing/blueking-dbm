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

export default class ResourceTag {
  id: number; // 标签ID
  value: string; // 标签名
  creator: string; // 创建人
  create_at: string; // 创建时间
  count: number; // 绑定IP数量
  update_at: string; // 更新时间
  is_builtin: boolean; // 是否内置标签

  constructor(payload = {} as Partial<ResourceTag>) {
    this.id = payload.id || 0;
    this.value = payload.value || '--';
    this.count = payload.count || 0;
    this.creator = payload.creator || '--';
    this.create_at = payload.create_at || '';
    this.update_at = payload.update_at || '';
    this.is_builtin = payload.is_builtin || false;
  }

  get isNewCreated() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get creationTimeDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get updatedAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

  get isBinded() {
    return this.count > 0;
  }

  get tag() {
    return this.value;
  }
}
