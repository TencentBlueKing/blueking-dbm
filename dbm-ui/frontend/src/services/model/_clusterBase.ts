import _ from 'lodash';

import type { ClusterListNode } from '@services/types';

import { isRecentDays, utcDisplayTime } from '@utils';

export default class ClusterBase {
  static getRoleFaildInstanceList = (data: ClusterListNode[]) => _.filter(data, (item) => item.status !== 'running');

  create_at: string;
  phase: string;
  update_at: string;

  constructor(payload: ClusterBase) {
    this.create_at = payload.create_at;
    this.phase = payload.phase;
    this.update_at = payload.update_at;
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isNew() {
    return isRecentDays(this.create_at, 24);
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

  get masterDomain() {
    return this.master_domain || this.domain;
  }
}
