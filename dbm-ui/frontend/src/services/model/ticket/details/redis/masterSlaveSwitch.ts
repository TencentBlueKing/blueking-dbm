import type { DetailBase, DetailClusters } from '../common';

export interface MasterSlaveSwitch extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: {
    cluster_id?: number; // 旧协议，兼容旧单据用
    cluster_ids: number[];
    online_switch_type: 'user_confirm' | 'no_confirm';
    pairs: {
      redis_master: string;
      redis_slave: string;
    }[];
  }[];
}
