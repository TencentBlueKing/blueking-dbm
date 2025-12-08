import type { ResourcePoolDetailBase } from '../../resource-pool';

// redis 主从迁移
export interface MigrateSingle extends ResourcePoolDetailBase {
  infos: {
    cluster_id?: number; // 历史协议
    db_version: string;
    // 历史协议
    display_info?: {
      domain: string;
      ip: string;
      migrate_type: string; // domain | machine
    };
    migrate_domain?: string; // 展示用
    migrate_ip?: string; // 展示用
    migrate_type: string; // 展示用，domain | machine, 分别对应migrate_domain和migrate_ip
    old_nodes?: MigrateSingle['infos'][number]['origin_old_nodes']; // 历史协议
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
