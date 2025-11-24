export default class ReleaseVersion {
  create_at: string;
  creator: string;
  db_type: string;
  engine: string;
  id: number;
  name: string;
  pkg_type: string;
  update_at: string;
  updater: string;
  version_series_count: number;

  constructor(payload = {} as ReleaseVersion) {
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.db_type = payload.db_type;
    this.engine = payload.engine;
    this.id = payload.id;
    this.name = payload.name;
    this.pkg_type = payload.pkg_type;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.version_series_count = payload.version_series_count;
  }

  get isDeleteDisabled() {
    return this.version_series_count > 0;
  }
}
