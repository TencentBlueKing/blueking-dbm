import type { DetailBase, DetailClusters } from '../common';

export interface SwitchNodes extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    switch_instances: {
      host: string;
      port: number;
      repl_binlog_file: string;
      repl_binlog_pos: number;
      target_pos: string;
    }[];
  }[];
  is_safe: boolean;
}
