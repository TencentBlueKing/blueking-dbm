import { t } from '@/locales/index';

export enum DBARoleTypes {
  /** 备 DBA */
  BACKUP_DBA = 'standby_dba',
  /** 二线 DBA */
  LEVEL2_DBA = 'sec_dba',
  /** 主 DBA */
  PRIMARY_DBA = 'primary_dba',
}

export const dbaRoleTypesInfo = {
  [DBARoleTypes.BACKUP_DBA]: {
    id: DBARoleTypes.BACKUP_DBA,
    tagText: t('备'),
    tagTheme: 'success' as const,
    text: t('备 DBA'),
  },
  [DBARoleTypes.LEVEL2_DBA]: {
    id: DBARoleTypes.LEVEL2_DBA,
    tagText: t('二线'),
    tagTheme: 'warning' as const,
    text: t('二线 DBA'),
  },
  [DBARoleTypes.PRIMARY_DBA]: {
    id: DBARoleTypes.PRIMARY_DBA,
    tagText: t('主'),
    tagTheme: 'info' as const,
    text: t('主 DBA'),
  },
};
