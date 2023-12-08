export default class NoticGroup {
  bk_biz_id: number;
  create_at: string;
  creator: string;
  db_type: string;
  dba_sync: boolean;
  details: {
    alert_notice: {
      time_range: string,
      notify_config: {
        notice_ways: {
          name: string,
          receivers?: string[]
        } [],
        level: 3 | 2 | 1
      }[]
    }[]
  };
  id: number;
  is_built_in: boolean;
  monitor_duty_rule_id: number;
  monitor_group_id: number;
  name: string;
  receivers: {
    type: string,
    id: string
  }[];
  sync_at: string;
  update_at: string;
  updater: string;
  used_count: number;
  permission: {
    global_notify_group_create: boolean,
    global_notify_group_delete: boolean,
    global_notify_group_update: boolean,
    notify_group_create: boolean,
    notify_group_delete: boolean,
    notify_group_update: boolean,
  };

  constructor(payload = {} as NoticGroup) {
    this.bk_biz_id = payload.bk_biz_id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_type = payload.db_type;
    this.dba_sync = payload.dba_sync;
    this.details = payload.details;
    this.id = payload.id;
    this.is_built_in = payload.is_built_in;
    this.monitor_duty_rule_id = payload.monitor_duty_rule_id;
    this.monitor_group_id = payload.monitor_group_id;
    this.name = payload.name;
    this.receivers = payload.receivers || [];
    this.sync_at = payload.sync_at;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.used_count = payload.used_count;
    this.permission = payload.permission;
  }
}
