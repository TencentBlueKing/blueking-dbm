import type { DetailBase } from '../common';

export interface Enable extends DetailBase {
  is_only_add_slave_domain: boolean;
  cluster_ids: number[];
}
