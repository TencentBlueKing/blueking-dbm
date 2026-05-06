import type { DetailBase } from '../common';

/**
 * Mongos 修复实例状态
 */
export interface InstanceFixStatus extends DetailBase {
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    dry_run: boolean;
    instance_address: string;
    ip: string;
    master_domain: string;
    port: number;
  }[];
}
