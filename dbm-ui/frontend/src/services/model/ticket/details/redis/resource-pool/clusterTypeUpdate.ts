import { Affinity } from '@common/const';

import type { ResourcePoolDetailBase } from '../../common';

export interface ClusterTypeUpdate extends ResourcePoolDetailBase {
  data_check_repair_setting: {
    execution_frequency: string;
    type: string;
  };
  infos: {
    capacity: number;
    cluster_shard_num: number;
    current_cluster_type: string;
    current_shard_num: number;
    current_spec_id: number;
    db_version: string;
    future_capacity: number;
    online_switch_type: 'user_confirm';
    resource_spec: {
      backend_group: {
        affinity: string;
        count: number; // 机器组数
        label_names: string[]; // 标签名称列表，单据详情回显用
        labels: string[]; // 标签id列表
        spec_id: number;
      };
      proxy: {
        affinity: Affinity.CROS_SUBZONE;
        count: number;
        spec_id: number;
      };
    };
    src_cluster: number;
    target_cluster_type: string;
  }[];
}
