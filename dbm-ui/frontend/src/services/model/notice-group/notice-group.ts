import { DBTypes, MessageTypes } from '@common/const';

import { isRecentDays, utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class NoticGroup {
  static NoticeMethodList = [
    {
      icon: 'youjian',
      label: t('邮件'),
      type: MessageTypes.MAIL,
    },
    {
      icon: 'yuyin',
      label: t('语音'),
      type: MessageTypes.VOICE,
    },
    {
      icon: 'qiyeweixin',
      label: t('企微'),
      type: MessageTypes.RTX,
    },
    {
      icon: 'qiweiqunliao',
      label: t('企微群聊'),
      type: MessageTypes.WXWORK_BOT,
    },
  ];

  bk_biz_id: number;
  create_at: string;
  creator: string;
  db_type: string;
  dba_sync: boolean;
  details: {
    alert_notice: {
      notify_config: {
        level: 3 | 2 | 1;
        notice_ways: {
          name: string;
          receivers?: string[];
        }[];
      }[];
      time_range: string;
    }[];
    channels: string[];
  };
  id: number;
  is_built_in: boolean;
  monitor_duty_rule_id: number;
  monitor_group_id: number;
  name: string;
  permission: {
    // global_notify_group_update: boolean;
    // notify_group_create: boolean;
    // notify_group_delete: boolean;
    notify_group_manage: boolean;
    // notify_group_update: boolean;
  };
  receivers: {
    id: string;
    type: string;
  }[];
  sync_at: string;
  update_at: string;
  updater: string;
  used_count: Record<DBTypes, number>;

  constructor(payload = {} as NoticGroup) {
    this.bk_biz_id = payload.bk_biz_id;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_type = payload.db_type;
    this.dba_sync = payload.dba_sync;
    this.details = payload.details;
    this.id = payload.id;
    this.is_built_in = payload.is_built_in;
    this.monitor_duty_rule_id = payload.monitor_duty_rule_id;
    this.monitor_group_id = payload.monitor_group_id;
    this.name = payload.name;
    this.receivers = payload.receivers || [];
    this.sync_at = payload.sync_at;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.used_count = payload.used_count;
    this.permission = payload.permission || {};
  }

  get isNew() {
    return isRecentDays(this.create_at, 24);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }

  get usedCountTotal() {
    return Object.values(this.used_count).reduce((prevCount, currCount) => prevCount + currCount, 0);
  }
}
