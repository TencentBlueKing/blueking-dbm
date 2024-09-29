import type { DetailBase } from '../common';

/**
 * DB 实例权限克隆
 */

export interface InstanceCloneRules extends DetailBase {
  clone_type: string;
  clone_uid: string;
  clone_cluster_type: string;
  clone_data: {
    bk_cloud_id: number;
    cluster_domain: string;
    cluster_id: number;
    source: string;
    target: string;
  }[];
}
