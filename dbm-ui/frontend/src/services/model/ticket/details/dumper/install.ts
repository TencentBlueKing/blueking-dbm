import type { DetailBase, DetailClusters } from '../common';

export interface Install extends DetailBase {
  name: string;
  infos: {
    l5_cmdid: number;
    l5_modid: number;
    dumper_id: number;
    cluster_id: number;
    db_module_id: number;
    protocol_type: string;
    target_port: number;
    target_address: string;
    kafka_pwd: string;
  }[];
  add_type: string;
  clusters: DetailClusters;
  repl_tables: string[];
}
