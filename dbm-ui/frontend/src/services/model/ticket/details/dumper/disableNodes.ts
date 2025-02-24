import type { DetailBase } from '../common';

export interface DisableNodes extends DetailBase {
  dumper_instance_ids: number[];
  dumpers: {
    [key: string]: {
      add_type: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_id: number;
      creator: string;
      dumper_id: string;
      id: number;
      ip: string;
      listen_port: number;
      need_transfer: boolean;
      phase: string;
      proc_type: string;
      protocol_type: string;
      source_cluster: {
        bk_cloud_id: number;
        cluster_type: string;
        id: number;
        immute_domain: string;
        major_version: string;
        master_ip: string;
        master_port: number;
        name: string;
        region: string;
      };
      target_address: string;
      target_port: number;
      updater: string;
      version: string;
    };
  };
}
