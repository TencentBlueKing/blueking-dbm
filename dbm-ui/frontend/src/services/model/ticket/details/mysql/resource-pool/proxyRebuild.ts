import type { ResourcePoolDetailBase } from '../../resource-pool';

/**
 * MySQL Proxy 原地重建（故障修复类）
 * 在原主机重建异常 Proxy 实例进程，拓扑、IP、端口均保持不变
 */
export interface ProxyRebuild extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    rebuild_proxy_hosts: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
    }[];
  }[];
  is_safe: boolean;
}
