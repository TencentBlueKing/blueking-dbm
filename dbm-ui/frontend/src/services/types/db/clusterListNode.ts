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
    count: number;
    cpu: {
      max: number;
      min: number;
    };
    device_class: string[];
    id: number;
    mem: {
      max: number;
      min: number;
    };
    name: string;
    qps: {
      max: number;
      min: number;
    };
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[];
  };
  status: 'running' | 'unavailable';
  version: '';
}
