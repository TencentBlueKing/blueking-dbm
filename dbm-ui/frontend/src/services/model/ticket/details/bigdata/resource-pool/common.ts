import type { HostInfo } from '@services/types';

export interface Nodes {
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
}

interface ResourceSpecItem {
  affinity: string;
  count: number;
  hosts: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }[];
  location_spec: {
    city: string;
    sub_zone_ids: number[];
  };
  spec_id: number;
}

export interface ResourceSpec {
  broker: ResourceSpecItem;
  client: ResourceSpecItem;
  cold: ResourceSpecItem;
  datanode: ResourceSpecItem;
  hot: ResourceSpecItem;
  master: ResourceSpecItem;
  namenode: ResourceSpecItem;
  proxy: ResourceSpecItem;
  slave: ResourceSpecItem;
  zookeeper: ResourceSpecItem;
}

interface ExtInfoItem {
  expansion_disk: number;
  host_list: HostInfo[];
  shrink_disk: number;
  target_disk: number;
  total_disk: number;
  total_hosts: number;
}

export interface ExtInfo {
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
}
