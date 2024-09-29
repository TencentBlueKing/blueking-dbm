import type { HostInfo } from '@services/types';

import type { DetailBase, DetailClusters } from '../common';

export interface Replace extends DetailBase {
  clusters: DetailClusters;
  ip_source: string;
  cluster_id: number;
  new_nodes: {
    datanode: HostInfo[];
    hot: HostInfo[];
    cold: HostInfo[];
    master: HostInfo[];
    client: HostInfo[];
    namenode: HostInfo[];
    zookeeper: HostInfo[];
    broker: HostInfo[];
    proxy: HostInfo[];
    slave: HostInfo[];
  };
  old_nodes: {
    datanode: HostInfo[];
    hot: HostInfo[];
    cold: HostInfo[];
    master: HostInfo[];
    client: HostInfo[];
    namenode: HostInfo[];
    zookeeper: HostInfo[];
    broker: HostInfo[];
    proxy: HostInfo[];
    slave: HostInfo[];
  };
}
