import type { HostInfo } from '@services/types';

import type { DetailBase, DetailClusters } from '../common';

export interface Replace extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  ip_source: string;
  new_nodes: {
    broker: HostInfo[];
    client: HostInfo[];
    cold: HostInfo[];
    datanode: HostInfo[];
    hot: HostInfo[];
    master: HostInfo[];
    namenode: HostInfo[];
    proxy: HostInfo[];
    slave: HostInfo[];
    zookeeper: HostInfo[];
  };
  old_nodes: {
    broker: HostInfo[];
    client: HostInfo[];
    cold: HostInfo[];
    datanode: HostInfo[];
    hot: HostInfo[];
    master: HostInfo[];
    namenode: HostInfo[];
    proxy: HostInfo[];
    slave: HostInfo[];
    zookeeper: HostInfo[];
  };
}
