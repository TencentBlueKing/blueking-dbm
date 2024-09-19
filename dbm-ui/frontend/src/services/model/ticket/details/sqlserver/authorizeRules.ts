import type { DetailBase } from '../common';

export interface authorizeRules extends DetailBase {
  authorize_data: {
    user: string;
    target_instances: string[];
    access_dbs: string[];
    cluster_type: string;
  }[];
  authorize_uid: string;
  excel_url: string;
}
