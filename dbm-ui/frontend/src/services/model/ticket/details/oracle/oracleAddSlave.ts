import type { ResourcePoolDetailBase } from '../resource-pool';

export interface oracleAddSlave extends ResourcePoolDetailBase {
  db_version: string;
  infos: {
    cluster_id: number;
    old_master?: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    old_node: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    resource_spec: {
      oracle: {
        count: number;
        label_names?: string[];
        labels?: string[];
        spec_id: number;
      };
    };
  }[];
  upstream_type: 'master' | 'single' | 'slave';
}
