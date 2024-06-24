import { t } from '@locales/index';

/**
 * 集群实例状态
 */
export enum ClusterInstStatusKeys {
  RUNNING = 'running',
  UNAVAILABLE = 'unavailable',
  RESTORING = 'restoring',
}
export const clusterInstStatus = {
  [ClusterInstStatusKeys.RUNNING]: {
    theme: 'success',
    text: t('正常'),
    key: ClusterInstStatusKeys.RUNNING,
  },
  [ClusterInstStatusKeys.UNAVAILABLE]: {
    theme: 'danger',
    text: t('异常'),
    key: ClusterInstStatusKeys.UNAVAILABLE,
  },
  [ClusterInstStatusKeys.RESTORING]: {
    theme: 'loading',
    text: t('重建中'),
    key: ClusterInstStatusKeys.RESTORING,
  },
};
export type ClusterInstStatus = `${ClusterInstStatusKeys}`;
