import type { HostInfo } from '@services/types';

import type { DetailBase, DetailClusters } from '../common';

export interface Shrink extends DetailBase {
  clusters: DetailClusters;
  cluster_id: number;
  ip_source: 'manual_input' | 'resource_pool';
  nodes: {
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
  resource_spec: {
    [key: string]: {
      count: number;
      instance_num?: number;
      spec_id: number;
    };
  };
  ext_info: {
    [key: string]: {
      host_list: {
        alive: number;
        disk: number;
      }[];
      total_hosts: number;
      total_disk: number;
      target_disk: number;
      expansion_disk: number;
      shrink_disk: number;
    };
  };
}
