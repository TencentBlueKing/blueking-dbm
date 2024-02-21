import dayjs from 'dayjs';

export default class SqlServerBase {
  create_at: string;

  constructor(payload: SqlServerBase) {
    this.create_at = payload.create_at;
  }

  get isNew(): boolean {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }
}
