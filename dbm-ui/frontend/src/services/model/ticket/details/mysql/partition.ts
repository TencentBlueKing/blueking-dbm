import type { DetailBase, DetailClusters } from '../common';

export interface Partition extends DetailBase {
  clusters: DetailClusters;
  infos: {
    config_id: string;
    cluster_id: number;
    bk_cloud_id: number;
    immute_domain: string;
    partition_objects: {
      ip: string;
      port: number;
      shard_name: string;
      execute_objects: [
        {
          dblike: string;
          tblike: string;
          config_id: number;
          add_partition: [];
          drop_partition: [];
          init_partition: [
            {
              sql: string;
              need_size: number;
            },
          ];
        },
      ];
    }[];
  }[];
}
