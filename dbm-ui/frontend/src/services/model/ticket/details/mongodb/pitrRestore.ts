import type { ClusterTypes } from '@common/const';

import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface PitrRestore extends DetailBase {
  cluster_ids: number[];
  cluster_type: ClusterTypes;
  clusters: DetailClusters;
  instance_per_host: number;
  resource_spec: {
    mongo_config: {
      count: number;
      spec_id: number;
    };
    mongodb: {
      count: number;
      spec_id: number;
    };
    mongos: {
      count: number;
      spec_id: number;
    };
  };
  rollback_time: {
    [clusterId: number]: string;
  };
  specs: DetailSpecs;
}
