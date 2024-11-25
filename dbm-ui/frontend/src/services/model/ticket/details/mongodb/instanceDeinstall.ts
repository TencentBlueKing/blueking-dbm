import type { DetailBase } from '../common';

export interface InstanceDeinstall extends DetailBase {
  infos: {
    ip: string;
    port: number;
    role: string;
    domain: string;
    bk_cloud_id: number;
  }[];
}
