import type { ResourcePoolDetailBase } from '../../common';

import type { Nodes, ResourceSpec } from './common';

interface ExtInfoItem {
  shrink_disk: number;
  total_disk: number;
  total_hosts: number;
}

/**
 * 大数据集群-缩容
 */
export interface Shrink extends ResourcePoolDetailBase {
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
  old_nodes: Nodes;
  resource_spec: ResourceSpec;
}
