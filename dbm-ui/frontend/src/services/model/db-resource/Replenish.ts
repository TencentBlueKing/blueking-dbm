/**
 * 创建补货单
 */
export interface CreateReplenish {
  db_type: string;
  spec_id: number;
  city: string;
  subzone: string;
  os_name: string;
  count: number;
}

/**
 * 补货单详情
 */
export default class Replenish implements CreateReplenish {
  db_type: string;
  spec_id: number;
  city: string;
  subzone: string;
  os_name: string;
  count: number;
  operator: string;
  spec: {
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
    device_class: string[];
    storage_spec: {
      max: number;
      min: number;
      size: number;
      type: string;
      mount_point: string;
    }[];
    instance_num: number;
    spec_id: number;
    spec_name: string;
    creator: string;
    updater: string;
    enable: boolean;
    desc: string;
    spec_cluster_type: string;
    spec_machine_type: string;
  };

  constructor(payload = {} as Replenish) {
    this.db_type = payload.db_type || '';
    this.spec_id = payload.spec_id || 0;
    this.city = payload.city || '';
    this.subzone = payload.subzone || '';
    this.os_name = payload.os_name || '';
    this.count = payload.count || 0;
    this.operator = payload.operator || '';
    this.spec = payload.spec || {};
  }
}
