import _ from 'lodash';

import type { ClusterListNode } from '@services/types';

import { isRecentDays, utcDisplayTime } from '@utils';

export default class ClusterBase {
  static getRoleFaildInstanceList = (data: ClusterListNode[]) => _.filter(data, (item) => item.status !== 'running');

  create_at: string;
  db_type: string;
  id: number;
  phase: string;
  tags: {
    id: number;
    is_builtin: boolean;
    key: string;
    system: boolean;
    value: string;
  }[];
  update_at: string;

  constructor(payload: ClusterBase) {
    this.create_at = payload.create_at;
    this.id = payload.id;
    this.db_type = payload.db_type;
    this.phase = payload.phase;
    this.tags = payload.tags || [];
    this.update_at = payload.update_at;
  }

  get availableTags() {
    return _.sortBy(this.tags, (item) => item.key).filter((item) => !item.system);
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get isNew() {
    return isRecentDays(this.create_at, 24);
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get masterDomain() {
    return this.master_domain || this.domain;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
