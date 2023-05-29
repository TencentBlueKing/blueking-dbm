import type { HostDetails } from '../../types';

export default class ImportHost implements HostDetails {
  alive: number;
  biz: { id: number; name: string };
  cloud_area: { id: number; name: string };
  cloud_id: number;
  host_id: number;
  host_name: string;
  ip: string;
  ipv6: string;
  meta: HostDetails['meta'];
  scope_id: string;
  scope_type: string;
  os_name: string;
  bk_cpu: number;
  bk_disk: number;
  bk_mem: number;
  os_type: string;
  agent_id: number;
  cpu: string;
  cloud_vendor: string;
  bk_idc_name: string;
  occupancy: boolean;

  constructor(payload = {} as ImportHost) {
    this.alive = payload.alive;
    this.biz = payload.biz;
    this.cloud_area = payload.cloud_area;
    this.cloud_id = payload.cloud_id;
    this.host_id = payload.host_id;
    this.host_name = payload.host_name;
    this.ip = payload.ip;
    this.ipv6 = payload.ipv6;
    this.meta = payload.meta;
    this.scope_id = payload.scope_id;
    this.scope_type = payload.scope_type;
    this.os_name = payload.os_name;
    this.bk_cpu = payload.bk_cpu || 0;
    this.bk_disk = payload.bk_disk || 0;
    this.bk_mem = payload.bk_mem || 0;
    this.os_type = payload.os_type;
    this.agent_id = payload.agent_id;
    this.cpu = payload.cpu;
    this.cloud_vendor = payload.cloud_vendor;
    this.bk_idc_name = payload.bk_idc_name;
    this.occupancy = payload.occupancy;
  }
}
