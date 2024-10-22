export interface MachineSpecConfig {
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
}
