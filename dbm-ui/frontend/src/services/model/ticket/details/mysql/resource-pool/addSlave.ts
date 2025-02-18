import type { DetailBase, DetailClusters } from '../../common';

/**
 * MySQL 添加从库
 */

export interface AddSlave extends DetailBase {
  clusters: DetailClusters;
  ip_source: 'resource_pool';
  infos: {
    cluster_ids: number[];
    resource_spec: {
      new_slave: {
        spec_id: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
    };
  }[];
  backup_source: string;
}
