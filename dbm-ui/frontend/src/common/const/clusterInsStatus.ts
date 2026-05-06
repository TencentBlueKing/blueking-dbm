import { t } from '@locales/index';

/**
 * 集群实例状态
 */
export enum ClusterInstStatusKeys {
  RESTORING = 'restoring',
  RUNNING = 'running',
  UNAVAILABLE = 'unavailable',
  UPGRADING = 'upgrading',
}
export const clusterInstStatus = {
  [ClusterInstStatusKeys.RESTORING]: {
    icon: 'sync-pending',
    key: ClusterInstStatusKeys.RESTORING,
    text: t('重建中'),
  },
  [ClusterInstStatusKeys.RUNNING]: {
    icon: 'normal',
    key: ClusterInstStatusKeys.RUNNING,
    text: t('运行中'),
  },
  [ClusterInstStatusKeys.UNAVAILABLE]: {
    icon: 'abnormal',
    key: ClusterInstStatusKeys.UNAVAILABLE,
    text: t('不可用'),
  },
  [ClusterInstStatusKeys.UPGRADING]: {
    icon: 'sync-pending',
    key: ClusterInstStatusKeys.UPGRADING,
    text: t('升级中'),
  },
};
export type ClusterInstStatus = `${ClusterInstStatusKeys}`;
