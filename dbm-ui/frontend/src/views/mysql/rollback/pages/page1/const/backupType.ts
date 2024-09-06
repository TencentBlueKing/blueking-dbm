import { t } from '@locales/index';

export enum BackupTypes {
  BACKUPID = 'BACKUPID',
  TIME = 'TIME',
}

export const backupTypeList = [
  {
    value: BackupTypes.BACKUPID,
    label: t('备份记录'),
  },
  {
    value: BackupTypes.TIME,
    label: t('回档到指定时间'),
  },
];
