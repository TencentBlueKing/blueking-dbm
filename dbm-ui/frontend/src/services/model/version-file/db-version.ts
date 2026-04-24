export default class DbVersion {
  create_at: string;
  creator: string;
  description: string;
  distribution_snapshot: object;
  enable: boolean;
  full_version: string;
  id: number;
  name: string;
  packages: {
    allow_biz_ids: number[];
    create_at: string;
    creator: string;
    db_type: string;
    db_version: number;
    enable: boolean;
    id: number;
    instances: number;
    md5: string;
    mode: string;
    name: string;
    path: string;
    permit_os: string[];
    permit_os_type: string;
    pkg_type: string;
    priority: number;
    size: number;
    update_at: string;
    updater: string;
    version: string;
  }[];
  phase: string;
  recommend: boolean;
  update_at: string;
  updater: string;
  version_series: number;

  constructor(payload = {} as DbVersion) {
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.description = payload.description;
    this.distribution_snapshot = payload.distribution_snapshot;
    this.enable = payload.enable;
    this.full_version = payload.full_version;
    this.id = payload.id;
    this.phase = payload.phase;
    this.recommend = payload.recommend;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.version_series = payload.version_series;
    this.packages = payload.packages;
    this.name = payload.name;
  }
}
