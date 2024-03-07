import type { DetailBase } from '../common';

export interface Reset extends DetailBase {
  infos: {
    cluster_id: number;
    new_cluster_name: string;
    new_immutable_domain: string;
    new_slave_domain: string;
  }[];
}
