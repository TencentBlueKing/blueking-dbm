import type { MachineRelatedCluster, MachineRelatedInstance } from '@services/types';

export default class RemotePaisInstance {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  instance: string;
  ip: string;
  name: string;
  phase: string;
  port: number;
  related_clusters: MachineRelatedCluster[];
  related_instances: MachineRelatedInstance[];
  related_pair_instances: MachineRelatedInstance[];
  spec_config: {
    id: number;
  };
  status: string;

  constructor(payload = {} as RemotePaisInstance) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.bk_instance_id = payload.bk_instance_id;
    this.instance = payload.instance;
    this.ip = payload.ip;
    this.name = payload.name;
    this.port = payload.port;
    this.phase = payload.phase;
    this.related_clusters = payload.related_clusters;
    this.related_instances = payload.related_instances;
    this.related_pair_instances = payload.related_pair_instances;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
  }
}
