import type { DetailBase } from '../common';

export interface Destroy extends DetailBase {
  force: boolean;
  cluster_ids: number[];
}
