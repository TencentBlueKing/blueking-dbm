import type { DetailBase } from '../common';

export interface InstanceDeinstall extends DetailBase {
  infos: {
    bk_cloud_id: number;
    domain: string;
    ip: string;
    port: number;
    role: string;
  }[];
}
