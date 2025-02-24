import type { DetailBase } from '../common';

export interface authorizeRules extends DetailBase {
  authorize_data: {
    access_dbs: string[];
    cluster_type: string;
    target_instances: string[];
    user: string;
  }[];
  authorize_uid: string;
  excel_url: string;
}
