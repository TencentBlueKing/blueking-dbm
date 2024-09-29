import type { DetailBase } from '../common';

export interface EnableNodes extends DetailBase {
  dumpers: {
    [key: string]: {
      id: number;
      ip: string;
      phase: string;
      creator: string;
      updater: string;
      version: string;
      add_type: string;
      bk_biz_id: number;
      dumper_id: string;
      proc_type: string;
      cluster_id: number;
      bk_cloud_id: number;
      listen_port: number;
      target_port: number;
      need_transfer: boolean;
      protocol_type: string;
      source_cluster: {
        id: number;
        name: string;
        region: string;
        master_ip: string;
        bk_cloud_id: number;
        master_port: number;
        cluster_type: string;
        immute_domain: string;
        major_version: string;
      };
      target_address: string;
    };
  };
  dumper_instance_ids: number[];
}
