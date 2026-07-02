import { utcDisplayTime } from '@utils';

export default class TicketFlowDescribe {
  bk_biz_id: number;
  cluster_ids: number[];
  clusters: {
    cluster_id: number;
    immute_domain: string;
  }[];
  configs: {
    expire_config: {
      flow_todo_expire: number;
      inner_flow_expire: number;
      itsm_expire: number;
    };
    need_itsm: boolean;
    need_manual_confirm: boolean;
  };
  creator: string;
  editable: boolean;
  flow_desc: string[];
  group: string;
  has_child_config: boolean;
  id: number;
  is_child_config: boolean;
  parent_id: number;
  permission: {
    biz_ticket_config_set: boolean;
    ticket_config_set: boolean;
  };
  remark: string;
  ticket_type: string;
  ticket_type_display: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as TicketFlowDescribe) {
    this.bk_biz_id = payload.bk_biz_id || 0;
    this.cluster_ids = payload.cluster_ids || [];
    this.clusters = payload.clusters || [];
    this.configs = payload.configs || {
      expire_config: {
        flow_todo_expire: -1,
        inner_flow_expire: -1,
        itsm_expire: -1,
      },
      need_itsm: true,
      need_manual_confirm: true,
    };
    this.creator = payload.creator || '';
    this.editable = payload.editable || false;
    this.flow_desc = payload.flow_desc || [];
    this.group = payload.group || '';
    this.has_child_config = payload.has_child_config || false;
    this.id = payload.id || 0;
    this.is_child_config = payload.is_child_config || false;
    this.parent_id = payload.parent_id || 0;
    this.permission = payload.permission || {
      biz_ticket_config_set: false,
      ticket_config_set: false,
    };
    this.remark = payload.remark || '';
    this.ticket_type = payload.ticket_type || '';
    this.ticket_type_display = payload.ticket_type_display || '';
    this.update_at = payload.update_at || '';
    this.updater = payload.updater || '';
  }

  // 集群列表
  get clusterDomainList() {
    return this.clusters.map((cluster) => cluster.immute_domain);
  }

  // 是否业务策略（当前业务的策略）
  get isBusinessPolicy() {
    return this.bk_biz_id !== 0;
  }

  // 是否子策略
  get isChildPolicy() {
    return this.is_child_config;
  }

  // 是否自定义（业务策略已自定义，与全局策略脱钩）
  get isCustom() {
    return this.isBusinessPolicy && this.has_child_config;
  }

  // 是否内置（全局策略）
  get isDefaultPolicy() {
    return this.bk_biz_id === 0;
  }

  // 是否父策略
  get isParentPolicy() {
    return this.has_child_config;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
