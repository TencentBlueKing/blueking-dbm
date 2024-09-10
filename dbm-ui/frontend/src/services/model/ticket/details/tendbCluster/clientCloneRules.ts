import type { DetailBase } from '../common';

/**
 * TenDB Cluster 客户端权限克隆
 */

export interface ClientCloneRules extends DetailBase {
  clone_type: string;
  clone_uid: string;
  clone_cluster_type: string;
  clone_data: {
    bk_cloud_id: number;
    source: string;
    target: string[];
    module: string;
  }[];
}
