import { RollbackClusterTypes } from '@services/model/ticket/details/mysql';

import { t } from '@locales/index';

export enum BackupSources {
  REMOTE = 'remote',
  LOCAL = 'local',
}
export enum BackupTypes {
  BACKUPID = 'BACKUPID',
  TIME = 'TIME',
}
export const selectList = {
  backupSource: [
    {
      value: BackupSources.REMOTE,
      label: t('远程备份'),
    },
    {
      value: BackupSources.LOCAL,
      label: t('本地备份'),
    },
  ],
  mode: [
    {
      value: BackupTypes.BACKUPID,
      label: t('备份记录'),
    },
    {
      value: BackupTypes.TIME,
      label: t('回档到指定时间'),
    },
  ],
};
export const rollbackInfos = {
  [RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER]: {
    value: RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER,
    label: t('构造到新集群'),
  },
  [RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER]: {
    value: RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER,
    label: t('构造到已有集群'),
  },
  [RollbackClusterTypes.BUILD_INTO_METACLUSTER]: {
    value: RollbackClusterTypes.BUILD_INTO_METACLUSTER,
    label: t('构造到原集群'),
  },
};
