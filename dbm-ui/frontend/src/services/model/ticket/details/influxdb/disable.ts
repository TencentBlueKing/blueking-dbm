import type { DetailBase } from '../common';

export interface Disable extends DetailBase {
  instance_list: {
    bk_cloud_id: number;
    bk_host_id: number;
    instance_id: number;
    ip: string;
    port: number;
  };
}
