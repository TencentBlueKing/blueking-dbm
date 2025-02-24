import type { DetailBase } from '../common';

/**
 * TenDB Cluster 客户端权限克隆
 */

export interface ClientCloneRules extends DetailBase {
  clone_cluster_type: string;
  clone_data: {
    bk_cloud_id: number;
    module: string;
    source: string;
    target: string[];
  }[];
  clone_type: string;
  clone_uid: string;
}
