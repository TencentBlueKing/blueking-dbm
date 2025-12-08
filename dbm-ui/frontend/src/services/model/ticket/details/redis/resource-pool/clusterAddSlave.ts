import type { MachineSpecConfig } from '@services/types';

import type { ResourcePoolDetailBase } from '../../resource-pool';

export interface ClusterAddSlave extends ResourcePoolDetailBase {
  infos: {
    bk_cloud_id: number;
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    old_nodes: {
      redis_slave: {
        bk_host_id: number;
        ip: string;
        spec: MachineSpecConfig;
      }[];
    };
    pairs: {
      redis_master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      redis_slave: {
        bk_cloud_id: number;
        bk_host_id: number;
        count?: number; // 历史协议
        ip: string;
        old_slave_ip?: string; // 历史协议
        spec_id?: number; // 历史协议
      };
    }[];
    resource_spec: {
      [key: `redis_slave_${string}`]: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
