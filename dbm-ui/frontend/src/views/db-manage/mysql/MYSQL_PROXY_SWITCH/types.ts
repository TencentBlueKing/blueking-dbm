/**
 * INSTANCE_REPLACE: 实例替换
 * HOST_REPLACE: 整机替换
 */
export enum ProxyReplaceTypes {
  INSTANCE_REPLACE = 'INSTANCE_REPLACE',
  HOST_REPLACE = 'HOST_REPLACE',
}

export interface TicketInfo {
  cluster_ids: number[];
  origin_proxy: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port?: number;
    instance_address?: string;
  };
  target_proxy: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  };
  display_info: {
    type: ProxyReplaceTypes;
    related_clusters: string[];
  };
}
