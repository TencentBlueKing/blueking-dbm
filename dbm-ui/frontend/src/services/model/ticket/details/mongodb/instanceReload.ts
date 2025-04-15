import type { DetailBase, DetailClusters, DetailInstances } from '../common';

export interface InstanceReload extends DetailBase {
  clusters: DetailClusters;
  infos: {
    bk_host_id: number;
    cluster_id: number;
    instance_id: number;
    port: number;
    role: string;
  }[];
  instances: DetailInstances;
}
