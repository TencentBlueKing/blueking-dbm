import {
  utcDisplayTime,
} from '@utils';

export default class ipWhite {
  bk_biz_id: number;
  create_at: string;
  creator: string;
  id: number;
  ips: string[];
  is_global: boolean;
  remark: string;
  update_at: string;
  updater: string;
  permission: {
    global_ip_whitelist_manage: boolean;
    ip_whitelist_manage: boolean;
  };

  constructor(payload = {} as ipWhite) {
    this.bk_biz_id = payload.bk_biz_id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.ips = payload.ips || [];
    this.is_global = payload.is_global;
    this.remark = payload.remark;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.permission = payload.permission || {};
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
