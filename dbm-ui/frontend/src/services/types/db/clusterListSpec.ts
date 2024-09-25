export interface ClusterListSpec {
  cpu: {
    max: number;
    min: number;
  };
  creator: string;
  desc: string;
  device_class: string[];
  enable: boolean;
  instance_num: number;
  mem: {
    max: number;
    min: number;
  };
  qps: {
    max: number;
    min: number;
  };
  spec_cluster_type: string;
  spec_id: number;
  spec_machine_type: string;
  spec_name: string;
  storage_spec: {
    mount_point: string;
    size: number;
    type: string;
  }[];
  updater: string;
}
