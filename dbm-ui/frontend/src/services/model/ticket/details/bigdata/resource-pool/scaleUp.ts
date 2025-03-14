import type { ResourcePoolDetailBase } from '../../common';

import type { ResourceSpec } from './common';

interface ExtInfoItem {
  expansion_disk: number;
  total_disk: number;
  total_hosts: number;
}

/**
 * 大数据集群-扩容
 */
export interface ScaleUp extends ResourcePoolDetailBase {
  cluster_id: number;
  ext_info: {
    broker: ExtInfoItem;
    client: ExtInfoItem;
    cold: ExtInfoItem;
    datanode: ExtInfoItem;
    hot: ExtInfoItem;
    master: ExtInfoItem;
    namenode: ExtInfoItem;
    proxy: ExtInfoItem;
    slave: ExtInfoItem;
    zookeeper: ExtInfoItem;
  };
  resource_spec: ResourceSpec;
}
