
import InstancelistModel from '@services/model/mongodb/instance-list';

import { useGlobalBizs } from '@stores';

import http from '../http';

import type { ListBase } from '@/services/types/index';

const { currentBizId } = useGlobalBizs();

const instanceModel = new InstancelistModel();
const type = instanceModel.ClusterType;
const path = `/apis/mongodb/bizs/${currentBizId}/${type}`;

interface InstanceDetails {
  id: number;
  cluster_id: number;
  cluster_type: string;
  cluster_name: string;
  version: string;
  db_module_id: number;
  bk_cloud_id: number;
  bk_cloud_name: string;
  ip: string;
  port: number;
  shard: string;
  instance_address: string;
  bk_host_id: number;
  role: string;
  machine_type: string;
  master_domain: string;
  slave_domain: string;
  status: string;
  create_at: string;
  spec_config: string;
  bk_agent_id: string;
  bk_cpu: number;
  bk_disk: number;
  bk_host_innerip: string;
  bk_mem: number;
  bk_os_name: string;
  bk_idc_name: string;
  bk_idc_id: string;
  db_version: null;
}

export interface PayloadType {
  conf_type: string,
  level_name: string,
  level_value: number,
  meta_cluster_type: string,
  version: string
}


/**
 * 实例列表返回结果
 */
export type InstanceList = ListBase<InstancelistModel[]>

/**
 * 获取列表数据
 */
export function getUserList(params: {
  limit?: number,
  offset?: number,
} = {}) {
  return http.get<ListBase<InstancelistModel[]>>(`${path}/list_instances/`, params).then(data => ({
    ...data,
    results: data.results.map((item: InstancelistModel) => new InstancelistModel(item)),
  }));
}

/**
 * 获取实例详情
 */
export function getInstanceDetail(params: { instance_address: string, bk_biz_id: number, cluster_id: number }) {
  return http.get<InstanceDetails>(`${path}/retrieve_instance/`, params);
}
/**
 * 获取角色列表
 */
export function getRoleList(params: { limit?: number, offset?: number } = {}) {
  return http.get<[string]>(`${path}/get_instance_role/`, params);
}
