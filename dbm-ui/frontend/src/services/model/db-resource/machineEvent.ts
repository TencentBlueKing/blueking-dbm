import { MachineEvents, machineEventsDisplayMap } from '@common/const/machineEvents';

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

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
  ticket?: number;
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
    this.event = payload.event;
    this.id = payload.id;
    this.ip = payload.ip;
    this.ticket = payload.ticket;
    this.ticket_type_display = payload.ticket_type_display;
    this.to = payload.to;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
  }

  get eventDisplay() {
    return machineEventsDisplayMap[this.event];
  }

  get operationDetail() {
    switch (this.event) {
      case MachineEvents.IMPORT_RESOURCE:
        return t('从「n」业务 CMDB空闲机模块导入', { n: this.bk_biz_name });
      case MachineEvents.APPLY_RESOURCE:
        return this.eventDisplay;
      case MachineEvents.RETURN_RESOURCE:
        return this.ticket ? t('下架主机') : t('其他池退回资源池');
      case MachineEvents.TO_DIRTY:
        return this.eventDisplay;
      case MachineEvents.TO_RECYCLE:
        return t('其他池转入待回收池');
      case MachineEvents.TO_FAULT:
        return this.ticket ? t('下架主机') : t('其他池转入故障池');
      case MachineEvents.UNDO_IMPORT:
        return t('退回「n」业务 CMDB 空闲机模块', { n: this.bk_biz_name });
      case MachineEvents.RECYCLED:
        return t('退回「n」业务 CMDB 待回收模块', { n: this.bk_biz_name });
      default:
        return this.event;
    }
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
