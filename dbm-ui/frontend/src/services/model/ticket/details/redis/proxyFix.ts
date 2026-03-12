import type { DetailBase, DetailClusters } from '../common';

export interface ProxyFix extends DetailBase {
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    operate_type: 'PROXY_ENTRY_FIX';
    proxy: {
      bk_cloud_id: number;
      bk_host_id: number;
      bk_sub_zone: string; // 展示用
      city: string; // 展示用
      ip: string;
    }[];
    restart_proxy: boolean;
  }[];
}
