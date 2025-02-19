import type { DetailBase, DetailClusters } from '../common';

export interface Install extends DetailBase {
  add_type: string;
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    db_module_id: number;
    dumper_id: number;
    kafka_pwd: string;
    l5_cmdid: number;
    l5_modid: number;
    protocol_type: string;
    target_address: string;
    target_port: number;
  }[];
  name: string;
  repl_tables: string[];
}
