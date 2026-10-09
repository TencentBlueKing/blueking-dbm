import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

/**
 * MySQL DTS 库改名迁移
 */

export interface DtsDataMigrateRename extends DetailBase {
  clusters?: DetailClusters;
  infos: {
    backup_locale: 'master' | 'slave';
    dts_resource: {
      deploy: {
        cluster_name: string;
        deploy_path: string;
        master_ha: boolean;
      };
      mode: string | null;
    };
    migrate: {
      one_to_one: {
        source: {
          cluster_id: number;
          sync_scope: {
            table_routes: {
              source_db: string;
              target_db: string;
            }[];
          };
        };
        target: {
          cluster_id: number;
          target_spider?: string | null;
        };
        task_name: string;
      };
      topology: 'one_to_one';
    };
    resource_spec: {
      master: {
        count: number;
        label_names?: string[];
        labels?: string[];
        spec_id: number;
      };
      worker: {
        count: number;
        label_names?: string[];
        labels?: string[];
        spec_id: number;
      };
    };
    source_role: 'master' | 'slave';
  }[];
  specs?: DetailSpecs;
  task: {
    on_duplicate: 'error' | 'replace' | 'ignore';
  };
}
