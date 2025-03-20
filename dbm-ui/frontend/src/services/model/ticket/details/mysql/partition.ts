import type { DetailBase, DetailClusters } from '../common';

export interface Partition extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_cloud_id: number;
    cluster_id: number;
    config_id: string;
    immute_domain: string;
    partition_objects: {
      execute_objects: [
        {
          add_partition: [];
          config_id: number;
          dblike: string;
          drop_partition: [];
          init_partition: [
            {
              need_size: number;
              sql: string;
            },
          ];
          tblike: string;
        },
      ];
      ip: string;
      port: number;
      shard_name: string;
    }[];
  }[];
}
