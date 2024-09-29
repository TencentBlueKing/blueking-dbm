import type { DetailBase } from '../common';

export interface AuthorizeRules extends DetailBase {
  authorize_data?: {
    auth_db: string;
    cluster_ids: number[];
    password: string;
    rule_sets: {
      db: string;
      privileges: string[];
    }[];
    username: string;
  }[];
  authorize_uid: string;
  excel_url?: string;
}
