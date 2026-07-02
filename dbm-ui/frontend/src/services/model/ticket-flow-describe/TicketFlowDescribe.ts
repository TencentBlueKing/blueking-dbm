import type { ClusterIdItem, ClusterTagItem } from '@services/source/ticket';

import { utcDisplayTime } from '@utils';

// 任意值匹配的标识值（与后端约定）
export const TAG_ANY_VALUE = '任意值';

// 子策略生效范围类型
export type ScopeType = 'cluster' | 'tag';

// 标签匹配条件类型
export type TagMatchType = 'single' | 'in' | 'exists';

export default class TicketFlowDescribe {
  bk_biz_id: number;
  cluster_ids: ClusterIdItem[];
  cluster_tags: ClusterTagItem[];
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
    need_itsm_duplicated: boolean;
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
    this.cluster_tags = payload.cluster_tags || [];
    this.configs = payload.configs || {
      expire_config: {
        flow_todo_expire: -1,
        inner_flow_expire: -1,
        itsm_expire: -1,
      },
      need_itsm: false,
      need_itsm_duplicated: false,
      need_manual_confirm: false,
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

  // 是否子策略
  get isChildPolicy() {
    return this.is_child_config;
  }

  // 是否自定义（业务策略即自定义，与全局策略脱钩）
  get isCustom() {
    return this.bk_biz_id !== 0;
  }

  // 是否内置（全局策略）
  get isDefaultPolicy() {
    return this.bk_biz_id === 0;
  }

  // 是否父策略
  get isParentPolicy() {
    return this.has_child_config;
  }

  /**
   * 标签键是否已失效（后端在 cluster_tags 每项返回 is_invalid 字段）
   * 父策略或按集群子策略返回 false；按标签子策略任一项 is_invalid 为 true 即视为失效
   */
  get isTagKeyInvalid(): boolean {
    if (this.scopeType !== 'tag' || !this.tagKey) return false;
    return this.cluster_tags.some((item) => item.is_invalid === true);
  }

  /**
   * 子策略生效范围类型
   * - cluster_tags 非空 → 按标签
   * - 否则 → 按集群（父策略也归为按集群，但其展示固定为「业务下全部集群」）
   */
  get scopeType(): ScopeType {
    return this.cluster_tags.length > 0 ? 'tag' : 'cluster';
  }

  /**
   * 标签生效范围展示文案
   * - 单值：键：v1
   * - 多值 in：键：（v1，v2，…）
   * - 任意值：键：任意值
   * - 失效态通过 CSS text-decoration: line-through 展示
   */
  get tagDisplay(): string {
    const key = this.tagKey;
    if (!key) return '';
    switch (this.tagMatchType) {
      case 'exists':
        return `${key} : ${TAG_ANY_VALUE}`;
      case 'in':
        return `${key} : ( ${this.tagValues.join(' , ')} )`;
      case 'single':
      default:
        return `${key} : ${this.tagValues[0] || ''}`;
    }
  }

  /**
   * 子策略标签键（每条子策略仅一个 tag_key）
   */
  get tagKey(): string {
    return this.cluster_tags[0]?.tag_key || '';
  }

  /**
   * 标签匹配条件类型
   * - exists：tag_value === '任意值'
   * - in：多条同 tag_key（多值）
   * - single：单条且非任意值
   */
  get tagMatchType(): TagMatchType {
    if (this.cluster_tags.length === 0) return 'single';
    if (this.cluster_tags.some((item) => item.tag_value === TAG_ANY_VALUE)) return 'exists';
    if (this.cluster_tags.length > 1) return 'in';
    return 'single';
  }

  /**
   * 标签具体值列表（exists 时为空）
   */
  get tagValues(): string[] {
    return this.cluster_tags.filter((item) => item.tag_value !== TAG_ANY_VALUE).map((item) => item.tag_value);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
