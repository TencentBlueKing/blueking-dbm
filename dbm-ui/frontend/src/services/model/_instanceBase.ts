import { ClusterInstStatusKeys } from '@common/const';

import { isRecentDays, utcDisplayTime } from '@utils';

export default class InstanceBase {
  create_at: string;
  status: string;

  constructor(payload: InstanceBase) {
    this.create_at = payload.create_at;
    this.status = payload.status;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get isNew() {
    return isRecentDays(this.create_at, 24);
  }

  get isUnavailable() {
    return this.status === ClusterInstStatusKeys.UNAVAILABLE;
  }
}
