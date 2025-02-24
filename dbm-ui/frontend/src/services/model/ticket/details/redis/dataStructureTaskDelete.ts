import type { DetailBase } from '../common';

export interface DataStructureTaskDelete extends DetailBase {
  infos: {
    bk_cloud_id: number;
    prod_cluster: string;
    related_rollback_bill_id: number;
  }[];
}
