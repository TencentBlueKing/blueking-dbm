import type { DetailBase, DetailClusters } from '../common';

export interface PartitionV2 extends DetailBase {
  cluster_id: number;
  cluster_type: string;
  clusters: DetailClusters;
  configs: {
    config_id: number;
    dblike: string;
    expire_time: number;
    extra_partition: number;
    partition_column: string;
    partition_column_type: string;
    partition_time_interval: number;
    partition_type: number;
    phase: string;
    tblike: string;
    time_zone: string;
  }[];
  force: boolean;
}
