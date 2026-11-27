import type { DetailBase, DetailClusters } from '../common';

export interface DtsExecHostSpec {
  label_names?: string[];
  labels?: string[];
  spec_id: number;
}

export interface Dts extends DetailBase {
  clusters: DetailClusters;
  infos: {
    // 资源池申请后由后端回填 bk_host_id / bk_cloud_id
    exec_host?: { bk_cloud_id?: number; bk_host_id?: number; ip?: string };
    exec_host_id?: number | null;
    exec_host_name?: string;
    namespaces?: string[];
    recycle_exec_host?: boolean;
    resource_spec?: { exec_host?: DtsExecHostSpec };
    source_cluster_id: number;
    source_connect_mode?: 'backup' | 'secondaryPreferred';
    stop_mode?: 'auto' | 'manual';
    target_cluster_id: number;
    transform_namespace?: string;
  }[];
}

export interface DtsCleanup extends DetailBase {
  clusters: DetailClusters;
  infos: {
    exec_host?: { ip?: string };
    exec_host_id?: number | null;
    recycle_exec_host?: boolean;
    source_cluster_id: number;
    source_root_id?: string;
    target_cluster_id: number;
  }[];
  source_root_id?: string;
}
