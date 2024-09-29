import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface Cutoff extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    mongos: {
      ip: string;
      spec_id: number;
    }[];
    mongodb: {
      ip: string;
      spec_id: number;
    }[];
    mongo_config: {
      ip: string;
      spec_id: number;
    }[];
  }[];
  ip_source: string;
  specs: DetailSpecs;
}
