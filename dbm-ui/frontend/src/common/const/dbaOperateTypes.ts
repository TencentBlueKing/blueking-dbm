import { t } from '@/locales/index';

export enum DBAOperateTypes {
  /** 取消纳管 */
  CANCEL_MANAGED = 'cancel_managed',
  /** 人员变更 */
  DBA_CHANGE = 'dba_change',
  /** 默认DBA变更 */
  DEFAULT_DBA_CHANGE = 'default_dba_change',
  /** 纳管 */
  MANAGED = 'managed',
  /** 标签变更 */
  TAG_CHANGE = 'tag_change',
}

/** 数据库配置层级信息 */
export const dbaOperateTypesInfo = {
  [DBAOperateTypes.CANCEL_MANAGED]: {
    id: DBAOperateTypes.CANCEL_MANAGED,
    text: t('取消纳管'),
    theme: 'danger' as const,
  },
  [DBAOperateTypes.DBA_CHANGE]: {
    id: DBAOperateTypes.DBA_CHANGE,
    text: t('人员变更'),
    theme: 'success' as const,
  },
  [DBAOperateTypes.DEFAULT_DBA_CHANGE]: {
    id: DBAOperateTypes.DEFAULT_DBA_CHANGE,
    text: t('默认DBA变更'),
    theme: '' as const,
  },
  [DBAOperateTypes.MANAGED]: {
    id: DBAOperateTypes.MANAGED,
    text: t('纳管业务'),
    theme: 'info' as const,
  },
  [DBAOperateTypes.TAG_CHANGE]: {
    id: DBAOperateTypes.TAG_CHANGE,
    text: t('标签变更'),
    theme: 'warning' as const,
  },
};
