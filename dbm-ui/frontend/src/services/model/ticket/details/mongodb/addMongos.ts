import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface AddMongos extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    resource_spec: {
      mongos: {
        count: number;
        spec_id: number;
      };
    };
    role: string;
  }[];
  ip_source: string;
  is_safe: boolean;
  specs: DetailSpecs;
}
