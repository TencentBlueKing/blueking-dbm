export interface ClusterListNode {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  bk_sub_zone: string;
  instance: string;
  ip: string;
  name: string;
  phase: string;
  port: number;
  spec_config: {
    id: number;
    cpu: {
      max: number;
      min: number;
    };
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    name: string;
    count: number;
    device_class: string[];
    storage_spec: {
      size: number;
      type: string;
      mount_point: string;
    }[];
  };
  status: 'running' | 'unavailable';
  version: '';
}
