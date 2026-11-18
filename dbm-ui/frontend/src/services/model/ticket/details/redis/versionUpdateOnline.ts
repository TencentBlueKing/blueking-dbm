import type { DetailBase, DetailClusters } from '../common';

export interface VersionUpdateOnline extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    cluster_ids: number[]; // 旧协议
    current_versions: string[];
    node_type: string;
    slave_current_versions: string[]; // 回显
    target_version: string; // 旧协议
    target_versions: {
      db_version_id?: number; // 新协议，提单传值
      instance_role: string; // 回显
      ip: string;
      related_clusters: string[]; // 回显
      slave_ip: string; // 回显
      version: string;
      version_name?: string; // 新协议，后台校验时写回
    }[];
  }[];
  update_type: string; // 回显
}
