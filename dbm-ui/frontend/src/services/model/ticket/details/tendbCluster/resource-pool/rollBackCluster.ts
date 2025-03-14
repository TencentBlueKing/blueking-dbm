import type { BackupLogRecord } from '@services/source/fixpointRollback';

import type { ResourcePoolDetailBase } from '../../common';

/**
 * TenDB Cluster 定点构造
 */

export interface RollbackCluster extends ResourcePoolDetailBase {
  apply_details: {
    bk_cloud_id: number;
    charset: string;
    city: string;
    cluster_name: string;
    cluster_shard_num: number;
    db_app_abbr: string;
    db_version: string;
    immutable_domain: string;
    ip_source: string;
    module: number;
    remote_shard_num: number;
    resource_spec: {
      backend_group: {
        count: number;
        spec_id: number;
      };
      spider: {
        count: number;
        spec_id: number;
      };
    };
    spider_port: number;
    spider_version: string;
  };
  ignore_check_db: boolean;
  infos: {
    backupinfo: BackupLogRecord;
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    resource_spec: {
      remote_hosts: {
        count: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
      spider_host: {
        count: number;
        hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spec_id: number;
      };
    };
    rollback_time: string;
    rollback_type: string;
    tables: string[];
    tables_ignore: string[];
    target_cluster_id: number;
  }[];
  rollback_cluster_type: 'BUILD_INTO_NEW_CLUSTER' | 'BUILD_INTO_EXIST_CLUSTER' | 'BUILD_INTO_METACLUSTER';
}
