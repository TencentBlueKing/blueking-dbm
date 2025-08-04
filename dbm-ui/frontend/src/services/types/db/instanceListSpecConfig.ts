export interface InstanceListSpecConfig {
  count: number;
  cpu: {
    max: number;
    min: number;
  };
  device_class: string;
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
    max: number;
    min: number;
    mount_point: string;
    type: string;
  }[];
}
