import type { DetailBase, DetailClusters, DetailInstances, DetailMachines } from '../common';

interface ClusterInfo {
  cluster_id: number;
}
interface InstanceInfo {
  bk_host_id: number;
  cluster_id: number;
  instance_id: number;
  port: number;
  role: string;
}

interface MachineInfo {
  bk_host_id: number;
  ip: string; // 展示用
  related_clusters: string[]; // 展示用
}

export interface InstanceReload extends DetailBase {
  clusters: DetailClusters;
  force: boolean;
  infos: (ClusterInfo | InstanceInfo | MachineInfo)[];
  instances: DetailInstances;
  machine_infos: DetailMachines;
  target_select_mode: 'cluster' | 'instance' | 'machine';
}
