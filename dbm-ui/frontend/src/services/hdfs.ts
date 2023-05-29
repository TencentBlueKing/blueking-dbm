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

import HdfsModel from '@services/model/hdfs/hdfs';
import ClusterConfigXmlsModel from '@services/model/hdfs/hdfs-cluster-config-xmls';
import HdfsInstanceModel from '@services/model/hdfs/hdfs-instance';
import HdfsNodeModel from '@services/model/hdfs/hdfs-node';
import HdfsPasswordModel from '@services/model/hdfs/hdfs-password';

import http from './http';
import type { ListBase } from './types';

//  获取集群列表
export const getList = function (params: Record<string, any> & { bk_biz_id: number }) {
  return http
    .get<ListBase<HdfsModel[]>>(`/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item: HdfsModel) => new HdfsModel(item)),
    }));
};

export const getPassword = function (params: Record<string, any> & { bk_biz_id: number; cluster_id: number }) {
  return http
    .get<HdfsPasswordModel>(
      `/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/${params.cluster_id}/get_password/`,
    )
    .then((data) => new HdfsPasswordModel(data));
};

// 获取 Hdfs 集群节点列表信息
export const getListNodes = function (params: Record<string, any> & { bk_biz_id: number; cluster_id: number }) {
  return http
    .get<
      ListBase<Array<HdfsNodeModel>>
    >(`/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/${params.cluster_id}/list_nodes/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map(
        (item) =>
          new HdfsNodeModel(
            Object.assign(item, {
              permission: data.permission,
            }),
          ),
      ),
    }));
};

// 获取查询返回字段
export const getTableFields = function (params: Record<string, any> & { bk_biz_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(
    `/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/get_table_fields/`,
  );
};

// 获取实例列表
export const getListInstance = function (params: Record<string, any> & { bk_biz_id: number }) {
  return http
    .get<
      ListBase<HdfsInstanceModel[]>
    >(`/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/list_instances/`, params)
    .then((data) => ({
      ...data,
      results: data.results.map((item: HdfsInstanceModel) => new HdfsInstanceModel(item)),
    }));
};

// 获取实例详情
export const getRetrieveInstance = function (params: { bk_biz_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(
    `/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/retrieve_instance/`,
    params,
  );
};

// 获取集群详情
export const getClusterDetail = function (params: { bk_biz_id: number; cluster_id: number }) {
  return http
    .get<HdfsModel>(`/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/${params.cluster_id}/`)
    .then((data) => new HdfsModel(data));
};

// 获取集群节点
export const getNodes = function (params: { bk_biz_id: number; cluster_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(
    `/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/${params.cluster_id}/get_nodes/`,
  );
};

// 获取集群拓扑
export const getTopoGraph = function (params: { bk_biz_id: number; cluster_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(
    `/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/${params.cluster_id}/get_topo_graph/`,
  );
};

// 获取集群访问xml配置
export const getClusterXmls = function (params: { bk_biz_id: number; cluster_id: number }) {
  return http.get<ClusterConfigXmlsModel>(
    `/apis/bigdata/bizs/${params.bk_biz_id}/hdfs/hdfs_resources/${params.cluster_id}/get_xmls/`,
  );
};
