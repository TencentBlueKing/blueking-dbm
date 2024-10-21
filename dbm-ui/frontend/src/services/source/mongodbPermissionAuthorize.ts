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

import http from '../http';

const getRootPath = () => `/apis/mongodb/bizs/${window.PROJECT_CONFIG.BIZ_ID}/permission/authorize`;

/**
 * MongoDB 授权规则前置检查
 */
export function preCheckAuthorizeRules(params: {
  mongo_users: {
    user: string;
    access_dbs: string[];
  }[];
  target_instances: string[];
  cluster_type: string;
  cluster_ids?: number[];
}) {
  return http.post<{
    authorize_data: {
      auth_db: string;
      cluster_ids: number[];
      password: string;
      rule_sets: {
        db: string;
        privileges: string[];
      }[];
      username: string;
    }[];
    authorize_uid: string;
    message: string;
    pre_check: boolean;
  }>(`${getRootPath()}/pre_check_rules/`, params);
}
