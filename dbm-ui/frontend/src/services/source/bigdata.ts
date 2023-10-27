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

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';
import EsNodeModel from '@services/model/es/es-node';
import EsPasswordModel from '@services/model/es/es-password';
import HdfsNodeModel from '@services/model/hdfs/hdfs-node';
import HdfsPasswordModel from '@services/model/hdfs/hdfs-password';
import KafkaNodeModel from '@services/model/kafka/kafka-node';
import KafkaPasswordModel from '@services/model/kafka/kafka-password';
import PulsarNodeModel from '@services/model/pulsar/pulsar-node';
import PulsarPasswordModel from '@services/model/pulsar/pulsar-password';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}`;

/**
 * 获取 ES 集群访问密码
 */
export const getESPassword = (params: {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<EsPasswordModel>(`${path}/es/es_resources/${params.cluster_id}/get_password/`)
  .then(data => new EsPasswordModel(data));

/**
 * 获取 ES 集群节点列表信息
 */
export const getESListNodes = (params: Record<string, any> & {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<ListBase<Array<EsNodeModel>>>(`${path}/es/es_resources/${params.cluster_id}/list_nodes/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: EsNodeModel) => new EsNodeModel(item)),
  }));

/**
 * 获取 HDFS 集群访问密码
 */
export const getHDFSPassword = (params: Record<string, any> & {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<HdfsPasswordModel>(`${path}/hdfs/hdfs_resources/${params.cluster_id}/get_password/`)
  .then(data => new HdfsPasswordModel(data));

/**
 * 获取 HDFS 集群节点列表信息
 */
export const getHDFSListNodes = (params: Record<string, any> & {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<ListBase<Array<HdfsNodeModel>>>(`${path}/hdfs/hdfs_resources/${params.cluster_id}/list_nodes/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: HdfsNodeModel) => new HdfsNodeModel(item)),
  }));

/**
 * 获取 Kafka 集群访问密码
 */
export const getKafkaPassword = (params: Record<string, any> & {
    bk_biz_id: number,
    cluster_id: number
  }) => http.get<KafkaPasswordModel>(`${path}/kafka/kafka_resources/${params.cluster_id}/get_password/`)
  .then(data => new KafkaPasswordModel(data));

/**
 * 获取 Kafka 集群节点列表信息
 */
export const getKafkaListNodes = (params: Record<string, any> & {
    bk_biz_id: number,
    cluster_id: number
  }) => http.get<ListBase<Array<KafkaNodeModel>>>(`${path}/kafka/kafka_resources/${params.cluster_id}/list_nodes/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: KafkaNodeModel) => new KafkaNodeModel(item)),
  }));

/**
 * 获取 Pulsar 集群访问密码
 */
export const getPulsarPassword = (params: Record<string, any> & {
    bk_biz_id: number,
    cluster_id: number
  }) => http.get<PulsarPasswordModel>(`${path}/pulsar/pulsar_resources/${params.cluster_id}/get_password/`)
  .then(data => new PulsarPasswordModel(data));

/**
 * 获取 Pulsar 集群节点列表信息
 */
export const getPulsarListNodes = (params: Record<string, any> & {
    bk_biz_id: number,
    cluster_id: number
  }) => http.get<ListBase<Array<PulsarNodeModel>>>(`${path}/pulsar/pulsar_resources/${params.cluster_id}/list_nodes/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: PulsarNodeModel) => new PulsarNodeModel(item)),
  }));

/**
 * 获取资源拓扑树
 */
export const getBusinessTopoTree = (params: {
  cluster_type: string,
  db_type: string,
  bk_biz_id: number
}) => http.get<BizConfTopoTreeModel[]>(`${path}/resource_tree/`, { cluster_type: params.cluster_type });
