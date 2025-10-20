import type { DetailBase, DetailClusters } from './common';
import type ReplenishModel from '@services/model/db-resource/Replenish';

export interface ResourcePoolRecycleHost {
  bk_agent_id: string;
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_cloud_vendor?: any;
  bk_cpu: number;
  bk_cpu_architecture: string;
  bk_cpu_module: string;
  bk_disk: number;
  bk_host_id: number;
  bk_host_innerip: string;
  bk_host_innerip_v6: string;
  bk_host_name: string;
  bk_host_outerip: string;
  bk_mem: number;
  bk_os_name: string;
  bk_os_type: string;
  city: string;
  device_class: string;
  host_id: number;
  ip: string;
  operator: string;
  os_name: string;
  os_type: string;
  rack_id: string;
  status: number;
  sub_zone: string;
}

/**
 * 已下架主机再利用
 */
export interface ResourcePoolRecycle extends DetailBase {
  group: string; // 回收机器的组件类型
  parent_ticket: number; // 关联的父单
  recycle_hosts: ResourcePoolRecycleHost[]; // 已下架主机
}

/**
 * 导入资源池
 */
export interface ImportResource extends DetailBase {
  bk_biz_id: number;
  for_biz: number;
  hosts: Array<{
    bk_cloud_id: number;
    bk_cloud_name: string;
    bk_os_name: string;
    city_name: string;
    host_id: number;
    ip: string;
    rack_id: string;
    status: number;
    sub_zone: string;
    svr_device_class: string;
  }>;
  label_names: string[];
  labels: number[];
  resource_type: string;
}

export interface ResourcePoolDetailBase extends DetailBase, Omit<ResourcePoolRecycle, 'group' | 'parent_ticket'> {
  clusters: DetailClusters;
  ip_recycle: {
    for_biz: number;
    ip_dest: 'resource';
  };
  ip_source: 'resource_pool';
}

/**
 * 资源池补货
 */
export interface ResourcePoolReplenish extends ReplenishModel {}
