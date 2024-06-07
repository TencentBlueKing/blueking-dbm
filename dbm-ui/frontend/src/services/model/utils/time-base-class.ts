import dayjs from 'dayjs';

import { utcDisplayTime } from '@utils';

export default class timeBaseClass {
  create_at: string;

  constructor(payload: timeBaseClass) {
    this.create_at = payload.create_at;
  }

  get isNew(): boolean {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }
}
