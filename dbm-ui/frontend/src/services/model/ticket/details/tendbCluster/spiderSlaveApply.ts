import type { DetailBase, DetailClusters, DetailSpecs, NodeInfo } from '../common';

/**
 *  TenDB Cluster 部署只读接入层
 */

export interface SpiderSlaveApply extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    resource_spec: {
      spider_slave_ip_list: {
        id: number;
        count: number;
        cpu: {
          max: number;
          min: number;
        };
        creator: string;
        desc: string;
        device_class: string[];
        enable: boolean;
        instance_num: number;
        mem: {
          max: number;
          min: number;
        };
        name: string;
        qps: {
          max: number;
          min: number;
        };
        spec_cluster_type: string;
        spec_id: number;
        spec_machine_type: string;
        spec_name: string;
        storage_spec: {
          size: number;
          type: string;
          mount_point: string;
        }[];
      };
    };
  }[];
  ip_source: string;
  nodes: Record<string, NodeInfo>;
  resource_request_id: string;
  specs: Record<string, DetailSpecs>;
}
