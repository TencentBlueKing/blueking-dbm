import { MachineEvents, machineEventsDisplayMap } from '@common/const/machineEvents';

import { utcDisplayTime } from '@utils';

// import { t } from '@locales/index';

export default class MachineEvent {
  bk_biz_id: number;
  bk_biz_name: string;
  bk_host_id: number;
  clusters: {
    id: number;
    immute_domain: string;
  }[];
  create_at: string;
  creator: string;
  db_app_abbr: string;
  event: MachineEvents;
  id: number;
  ip: string;
  remark: string;
  ticket?: number;
  ticket_type: string;
  ticket_type_display: string;
  to: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as MachineEvent) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_host_id = payload.bk_host_id;
    this.clusters = payload.clusters;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.db_app_abbr = payload.db_app_abbr;
    this.ticket_type = payload.ticket_type;
    this.event = payload.event;
    this.id = payload.id;
    this.ip = payload.ip;
    this.ticket = payload.ticket;
    this.ticket_type_display = payload.ticket_type_display;
    this.to = payload.to;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.remark = payload.remark;
  }

  get eventDisplay() {
    return machineEventsDisplayMap[this.event];
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
