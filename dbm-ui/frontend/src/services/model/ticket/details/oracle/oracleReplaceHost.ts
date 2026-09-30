import type { ResourcePoolDetailBase } from '../resource-pool';

// 协议主机要素（old_node / old_master 结构）
interface HostInfo {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  port: number;
  // 主机角色（primary/standby 等），单据详情快照展示
  role: string;
}

export interface oracleReplaceHost extends ResourcePoolDetailBase {
  // 前端拼接：Oracle-{实例版本号}
  db_version: string;
  flow_type: string;
  infos: {
    cluster_id: number;
    // 仅主从集群正常从库场景（级联）：old_master 为主库
    old_master?: HostInfo;
    old_node: HostInfo;
    replace_flag: boolean;
    // 页面所选主机（被替换主机）
    replace_host: HostInfo;
    resource_spec: {
      oracle: {
        count: number;
        label_names: string[];
        labels: string[];
        spec_id: number;
      };
    };
  }[];
  ip_source: 'resource_pool';
}
