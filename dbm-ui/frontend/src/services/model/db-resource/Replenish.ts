/**
 * 创建补货单
 */
export interface CreateReplenish {
  /** 地域（新口径必传，与 bk_cloud_zone 同时传；city 保留兼容） */
  bk_cloud_region: string;
  /** 可用区（新口径必传，与 bk_cloud_region 同时传；subzone 保留兼容） */
  bk_cloud_zone: string;
  // city: string;
  count: number;
  db_type: string;
  os_name: string;
  spec_id: number;
  // subzone: string;
}

/**
 * 补货单详情
 */
export default class Replenish implements CreateReplenish {
  bk_cloud_region: string;
  bk_cloud_zone: string;
  city: string;
  count: number;
  db_type: string;
  operator: string;
  os_name: string;
  record_id: number;
  spec: {
    cpu: {
      max: number;
      min: number;
    };
    creator: string;
    desc: string;
    device_class: string[];
    enable: boolean;
    instance_num: number;
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    spec_cluster_type: string;
    spec_id: number;
    spec_machine_type: string;
    spec_name: string;
    storage_spec: {
      max: number;
      min: number;
      mount_point: string;
      size: number;
      type: string;
    }[];
    updater: string;
  };
  spec_id: number;
  subzone: string;

  constructor(payload = {} as Replenish) {
    this.db_type = payload.db_type || '';
    this.spec_id = payload.spec_id || 0;
    this.city = payload.city || '';
    this.subzone = payload.subzone || '';
    this.bk_cloud_region = payload.bk_cloud_region || '';
    this.bk_cloud_zone = payload.bk_cloud_zone || '';
    this.os_name = payload.os_name || '';
    this.count = payload.count || 0;
    this.operator = payload.operator || '';
    this.spec = payload.spec || {};
    this.record_id = payload.record_id || 0;
  }
}
