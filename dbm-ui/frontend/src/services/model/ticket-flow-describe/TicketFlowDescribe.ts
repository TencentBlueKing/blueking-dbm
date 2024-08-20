import { utcDisplayTime } from '@utils';

export default class TicketFlowDescribe {
  bk_biz_id: number;
  cluster_ids: number[];
  clusters: {
    id: number;
    immute_domain: string;
  }[];
  configs: {
    need_itsm: boolean;
    need_manual_confirm: boolean;
  };
  creator: string;
  editable: boolean;
  flow_desc: string[];
  group: string;
  id: number;
  permission: {
    ticket_config_set: boolean;
  };
  ticket_type: string;
  ticket_type_display: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as TicketFlowDescribe) {
    this.bk_biz_id = payload.bk_biz_id;
    this.cluster_ids = payload.cluster_ids || [];
    this.clusters = payload.clusters || [];
    this.configs = payload.configs;
    this.creator = payload.creator;
    this.editable = payload.editable;
    this.flow_desc = payload.flow_desc || [];
    this.group = payload.group;
    this.id = payload.id;
    this.permission = payload.permission;
    this.ticket_type = payload.ticket_type;
    this.ticket_type_display = payload.ticket_type_display;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

  get isCustomTarget() {
    return this.bk_biz_id !== 0;
  }

  get clusterDomainList() {
    return this.clusters.map((cluster) => cluster.immute_domain);
  }
}
