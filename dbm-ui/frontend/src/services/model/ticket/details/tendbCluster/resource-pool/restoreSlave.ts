import type { DetailMachines, ResourcePoolDetailBase } from '../../common';

/**
 * TenDB Cluster Slave重建
 */
export interface RestoreSlave extends ResourcePoolDetailBase {
  backup_source: 'local' | 'remote';
  infos: {
    cluster_id: number;
    old_nodes: {
      old_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    resource_spec: {
      new_slave: {
        count: number;
        spec_id: number;
      };
    };
  }[];
  machine_infos: DetailMachines;
}
