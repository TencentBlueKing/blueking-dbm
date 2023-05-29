import { utcDisplayTime } from '@utils';

export default class VersionFile {
  allow_biz_ids: number[];
  create_at: string;
  creator: string;
  db_type: string;
  enable: boolean;
  id: number;
  md5: string;
  mode: string;
  name: string;
  path: string;
  pkg_type: string;
  priority: number;
  size: number;
  update_at: string;
  updater: string;
  version: string;
  permission: {
    package_manage: boolean;
  };

  constructor(payload = {} as VersionFile) {
    this.allow_biz_ids = payload.allow_biz_ids;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_type = payload.db_type;
    this.enable = payload.enable;
    this.id = payload.id;
    this.md5 = payload.md5;
    this.mode = payload.mode;
    this.name = payload.name;
    this.path = payload.path;
    this.pkg_type = payload.pkg_type;
    this.priority = payload.priority;
    this.size = payload.size;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.version = payload.version;
    this.permission = payload.permission || {};
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
