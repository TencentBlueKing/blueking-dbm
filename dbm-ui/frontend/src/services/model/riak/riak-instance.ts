import type { HostInfo, InstanceListSpecConfig, InstanceRelatedCluster } from '@services/types';

import { ClusterTypes } from '@common/const';

export default class RiakInstance {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_host_innerip: string;
  bk_idc_id: number;
  bk_idc_name: string;
  bk_idc_city_id: string;
  bk_idc_city_name: string;
  cluster_id: number;
  cluster_name: string;
  cluster_type: ClusterTypes;
  create_at: string;
  db_module_id: number;
  db_module_name: string;
  host_info: HostInfo;
  id: number;
  instance_address: string;
  ip: string;
  master_domain: string;
  port: number;
  related_clusters: InstanceRelatedCluster[];
  role: string;
  slave_domain: string;
  spec_config: InstanceListSpecConfig;
  status: string;
  version: string;

  constructor(payload = {} as RiakInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_host_innerip = payload.bk_host_innerip || '';
    this.bk_idc_id = payload.bk_idc_id || 0;
    this.bk_idc_name = payload.bk_idc_name || '';
    this.bk_idc_city_id = payload.bk_idc_city_id || '';
    this.bk_idc_city_name = payload.bk_idc_city_name || '';
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.host_info = payload.host_info || {};
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.ip = payload.ip;
    this.master_domain = payload.master_domain;
    this.port = payload.port;
    this.related_clusters = payload.related_clusters || [];
    this.role = payload.role;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
    this.version = payload.version;
  }
}
