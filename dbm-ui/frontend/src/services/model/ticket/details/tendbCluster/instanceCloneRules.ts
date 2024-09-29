import type { DetailBase } from '../common';

/**
 * TenDB Cluster DB 实例权限克隆
 */

export interface InstanceCloneRules extends DetailBase {
  clone_type: string;
  clone_uid: string;
  clone_cluster_type: string;
  clone_data: {
    bk_cloud_id: number;
    cluster_domain: string;
    cluster_id: number;
    module: string;
    source: string;
    target: string;
  }[];
}
