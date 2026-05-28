import type { ResourcePoolDetailBase } from '../../resource-pool';

/**
 * TenDBCluster 接入层原地重建（故障修复类）
 * 在原主机重建异常 Spider 实例进程，拓扑、IP、端口均保持不变
 */
export interface SpiderRebuild extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    rebuild_spider_role: string;
    spider_ip_list: {
      bk_cloud_id: number;
      ip: string;
    }[];
  }[];
}
