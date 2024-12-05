import type { DetailBase, DetailClusters } from '../common';

/**
 * TenDB Cluster Slave重建
 */
export interface RestoreSlave extends DetailBase {
  backup_source: 'local' | 'remote';
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    old_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    resource_spec: {
      new_slave: {
        count: number;
        cpu: {
          max: number;
          min: number;
        };
        device_class: string[];
        id: number;
        mem: {
          max: number;
          min: number;
        };
        name: string;
        qps: {
          max: number;
          min: number;
        };
        spec_id: number;
        storage_spec: {
          mount_point: string;
          size: number;
          type: string;
        }[];
      };
    };
  }[];
}
