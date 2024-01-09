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

import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import MongodbInstanceDetailModel from '@services/model/mongodb/mongodb-instance-detail';
import type { ListBase } from '@services/types/index';

import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mongodb/bizs/${currentBizId}/mongodb_resources`;

/**
 * 获取列表数据
 */
export function getInstanceList(params: {
  limit?: number,
  offset?: number,
}) {
  return http.get<ListBase<MongodbInstanceModel[]>>(`${path}/list_instances/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new MongodbInstanceModel(item)),
  }));
}

/**
 * 获取实例详情
 */
export function getInstanceDetail(params: {
  instance_address: string,
  cluster_id: number
}) {
  return http.get<MongodbInstanceDetailModel>(`${path}/retrieve_instance/`, params);
}

/**
 * 获取角色列表
 */
export function getRoleList(params: {
  limit?: number,
  offset?: number
}) {
  return http.get<string[]>(`${path}/get_instance_role/`, params);
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportMongodbInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}
