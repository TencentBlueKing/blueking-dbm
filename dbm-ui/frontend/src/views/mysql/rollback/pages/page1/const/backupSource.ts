import { t } from '@locales/index';

export enum BackupSources {
  REMOTE = 'remote',
  LOCAL = 'local',
}

export const backupSourceList = [
  {
    value: BackupSources.REMOTE,
    label: t('远程备份'),
  },
  {
    value: BackupSources.LOCAL,
    label: t('本地备份'),
  },
];
