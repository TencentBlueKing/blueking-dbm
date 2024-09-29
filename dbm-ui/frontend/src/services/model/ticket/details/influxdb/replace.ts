import type { DetailBase } from '../common';

export interface Replace extends DetailBase {
  new_nodes: {
    influxdb: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  };
  old_nodes: {
    influxdb: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  };
}
