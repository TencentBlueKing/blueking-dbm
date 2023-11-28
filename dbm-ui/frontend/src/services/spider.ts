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

import SpiderModel from '@services/model/spider/spider';
import TendbClusterModel from '@services/model/spider/tendbCluster';
import TendbInstanceModel from '@services/model/spider/tendbInstance';

import { useGlobalBizs } from '@stores';

import http from './http';
import type {
  ListBase,
  ResourceInstance,
} from './types';

const { currentBizId } = useGlobalBizs();

/**
 * 获取 spider 集群列表
 */
export function getSpiderList(params: Record<string, any> = {}) {
  return http.get<{
    count: number,
    results: TendbClusterModel[]
  }>(`/apis/mysql/bizs/${currentBizId}/spider_resources/`, params)
    .then(res => ({
      ...res,
      results: res.results.map(data => new TendbClusterModel(data)),
    }));
}

/**
 * 获取 spider 集群详情
 * @param id 集群 ID
 */
export const getSpiderDetails = (params: { id: number }) => http.get<TendbClusterModel>(`/apis/mysql/bizs/${currentBizId}/spider_resources/${params.id}/`);

/**
 * 获取 spider 实例列表
 */
export function getSpiderInstances(params: Record<string, any>) {
  return http.get<ListBase<TendbInstanceModel[]>>(`/apis/mysql/bizs/${currentBizId}/spider_resources/list_instances/`, params)
    .then(res => ({
      ...res,
      results: res.results.map(data => new TendbInstanceModel(data)),
    }));
}

/**
 * 获取 spider 实例详情
 */
export const getSpiderInstanceDetails = (params: {
  instance_address: string,
  cluster_id: number
}) => http.get<TendbInstanceModel>(`/apis/mysql/bizs/${currentBizId}/spider_resources/retrieve_instance/`, params);

export const getList = function (params: Record<string, any>) {
  const { currentBizId } = useGlobalBizs();

  return http.get<ListBase<SpiderModel[]>>(`/apis/mysql/bizs/${currentBizId}/spider_resources/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
    }));
};

export const getDetail = function (params: { id: number }) {
  const { currentBizId } = useGlobalBizs();

  return http.get<SpiderModel>(`/apis/mysql/bizs/${currentBizId}/spider_resources/${params.id}/`)
    .then(data => new SpiderModel(data));
};

/**
 * 获取集群实例列表
 */
export const listSpiderResourceInstances = (params: { bk_biz_id: number } & Record<string, any>) => http.get<ListBase<ResourceInstance[]>>(`/apis/mysql/bizs/${params.bk_biz_id}/spider_resources/list_instances/`, params);

