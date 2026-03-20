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

export interface ConfigNameChangeImage {
  conf_name_lc: string;
  description: string;
  flag_disable: number;
  flag_encrypt: number;
  flag_locked: number;
  flag_readonly: number;
  flag_visible: number;
  need_restart: number;
  since_version: string;
  value_allowed: string;
  value_default: string;
  value_type: string;
  value_type_sub: string;
}

export default class ConfigNameChange {
  after_image: ConfigNameChangeImage;
  before_image: ConfigNameChangeImage;
  conf_file: string;
  conf_file_lc: string;
  conf_name: string;
  conf_type: string;
  conf_type_lc: string;
  created_at: string;
  id: number;
  namespace: string;
  op_type: string;
  op_user: string;
  updated_at: string;

  constructor(payload = {} as ConfigNameChange) {
    this.after_image = payload.after_image;
    this.before_image = payload.before_image;
    this.conf_file = payload.conf_file;
    this.conf_file_lc = payload.conf_file_lc;
    this.conf_name = payload.conf_name;
    this.conf_type = payload.conf_type;
    this.conf_type_lc = payload.conf_type_lc;
    this.created_at = payload.created_at;
    this.id = payload.id;
    this.namespace = payload.namespace;
    this.op_type = payload.op_type;
    this.op_user = payload.op_user;
    this.updated_at = payload.updated_at;
  }
}
