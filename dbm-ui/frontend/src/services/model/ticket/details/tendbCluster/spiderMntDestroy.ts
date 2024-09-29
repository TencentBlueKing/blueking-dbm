import type { DetailBase } from '../common';

export interface SpiderMntDestroy extends DetailBase {
  is_safe: boolean;
  infos: {
    cluster_id: number;
    spider_ip_list: {
      ip: string;
      bk_cloud_id: number;
    }[];
  }[];
}
