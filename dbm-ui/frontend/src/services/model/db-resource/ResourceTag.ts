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
  create_at: string; // 创建时间
  creator: string; // 创建人
  id: number; // 标签ID
  is_builtin: boolean; // 是否内置标签
  update_at: string; // 更新时间
  value: string; // 标签名

  constructor(payload = {} as ResourceTag) {
    this.create_at = payload.create_at || '';
    this.creator = payload.creator || '';
    this.id = payload.id || 0;
    this.is_builtin = payload.is_builtin || false;
    this.update_at = payload.update_at || '';
    this.value = payload.value || '';
  }

  get isNewCreated() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get updatedAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
