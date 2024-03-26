import { utcDisplayTime } from '@utils';

export default class TicketFlowDescribe {
  configs: {
    need_itsm: boolean;
    need_manual_confirm: boolean;
  }
  creator: string;
  editable: boolean;
  flow_desc: string[];
  group: string;
  permission: {
    ticket_config_set: boolean;
  };
  ticket_type: string;
  ticket_type_display: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as TicketFlowDescribe){
    this.configs = payload.configs;
    this.creator = payload.creator;
    this.editable = payload.editable;
    this.flow_desc = payload.flow_desc || [];
    this.group = payload.group;
    this.permission = {
      ticket_config_set: false
    };
    this.ticket_type = payload.ticket_type;
    this.ticket_type_display = payload.ticket_type_display;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

}