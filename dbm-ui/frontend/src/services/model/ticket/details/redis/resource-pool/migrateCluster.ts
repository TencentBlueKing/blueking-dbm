import type { ResourcePoolDetailBase } from '../../common';

// redis 集群迁移
export interface MigrateCluster extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    db_version: string[]; // 展示用
    // 历史协议
    display_info?: {
      db_version: string[];
      instance: string;
    };
    migrate_instance: string; // 展示用
    old_nodes?: MigrateCluster['infos'][number]['origin_old_nodes']; // 历史协议
    origin_old_nodes: {
      master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
    };
    resource_spec: {
      backend_group: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
    src_cluster: {
      cluster_id: number;
      master_ins: string;
      slave_ins: string;
    }[];
  }[];
}
