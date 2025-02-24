import type { HostInfo } from '@services/types';

import type { DetailBase, DetailClusters } from '../common';

export interface ScaleUp extends DetailBase {
  cluster_id: number;
  clusters: DetailClusters;
  ext_info: {
    [key: string]: {
      expansion_disk: number;
      host_list: {
        alive: number;
        disk: number;
      }[];
      shrink_disk: number;
      target_disk: number;
      total_disk: number;
      total_hosts: number;
    };
  };
  ip_source: 'manual_input' | 'resource_pool';
  nodes: {
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
  resource_spec: {
    [key: string]: {
      count: number;
      instance_num?: number;
      spec_id: number;
    };
  };
}
