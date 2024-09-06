import { t } from '@locales/index';

export enum BackupSources {
  REMOTE = 'remote',
}

export const backupSourceList = [
  {
    value: BackupSources.REMOTE,
    label: t('远程备份'),
  },
];
