import { DBTypes } from '@common/const';

export default class RiskMemoDetail {
  biz_inpact: string[];
  bk_biz_id: number;
  create_at: string;
  creator: string;
  db_type: DBTypes;
  description: string;
  duration_time: number;
  final_content: string;
  final_time: number;
  finalist: string;
  follow_ups: {
    content: string;
    create_at: string;
    creator: string;
    id: number;
    is_follow_up_owner: boolean;
    risk: number;
    update_at: string;
    updater: string;
  }[];
  id: number;
  inpact_cluster: string[];
  is_special: boolean;
  level: string;
  name: string;
  special_status: string;
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as RiskMemoDetail) {
    this.biz_inpact = payload.biz_inpact;
    this.bk_biz_id = payload.bk_biz_id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_type = payload.db_type;
    this.description = payload.description;
    this.duration_time = payload.duration_time;
    this.final_content = payload.final_content;
    this.final_time = payload.final_time;
    this.finalist = payload.finalist;
    this.follow_ups = payload.follow_ups;
    this.id = payload.id;
    this.inpact_cluster = payload.inpact_cluster;
    this.is_special = payload.is_special;
    this.level = payload.level;
    this.name = payload.name;
    this.special_status = payload.special_status;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }
}
