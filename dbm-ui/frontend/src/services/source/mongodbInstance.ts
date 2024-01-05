import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import type { ListBase } from '@services/types/index';

import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mongodb/bizs/${currentBizId}/mongodb_resources`;

interface InstanceDetails {
  bk_agent_id: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_cpu: number;
  bk_disk: number;
  bk_host_id: number;
  bk_host_innerip: string;
  bk_idc_id: string;
  bk_idc_name: string;
  bk_mem: number;
  bk_os_name: string;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: number;
  db_version: null;
  id: number;
  instance_address: string;
  ip: string;
  machine_type: string;
  master_domain: string;
  port: number;
  role: string;
  shard: string;
  slave_domain: string;
  spec_config: string;
  status: string;
  version: string;
}

/**
 * 获取列表数据
 */
export function getUserList(params: {
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
  bk_biz_id: number,
  cluster_id: number
}) {
  return http.get<InstanceDetails>(`${path}/retrieve_instance/`, params);
}

/**
 * 获取角色列表
 */
export function getRoleList(params: {
  limit?: number,
  offset?: number
}) {
  return http.get<[string]>(`${path}/get_instance_role/`, params);
}
