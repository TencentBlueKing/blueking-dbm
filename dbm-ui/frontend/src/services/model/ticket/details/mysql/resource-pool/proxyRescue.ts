import type { ResourcePoolDetailBase } from '../../resource-pool';

/**
 * MySQL Proxy 故障重建（故障修复类）
 * 集群所选 Proxy 整组不可用、无法在原机器上立即恢复时（如大范围主机故障），
 * 按集群整组申请新机重建并下架旧机
 */
export interface ProxyRescue extends ResourcePoolDetailBase {
  infos: {
    auto_cleanup_old_proxies: boolean;
    cluster_id: number;
    old_nodes: {
      proxy: {
        bk_biz_id?: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        spec?: Record<string, unknown>;
      }[];
    };
    proxy_version: string;
    resource_spec: {
      new_proxies: {
        count: number;
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
    };
  }[];
}
