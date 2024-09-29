import type { DetailBase } from '../common';

export interface DataStructureTaskDelete extends DetailBase {
  infos: {
    related_rollback_bill_id: number;
    prod_cluster: string;
    bk_cloud_id: number;
  }[];
}
