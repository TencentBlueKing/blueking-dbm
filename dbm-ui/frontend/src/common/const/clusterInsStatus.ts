import { t } from '@locales/index';

/**
 * 集群实例状态
 */
export enum ClusterInstStatusKeys {
  RESTORING = 'restoring',
  RUNNING = 'running',
  UNAVAILABLE = 'unavailable',
}
export const clusterInstStatus = {
  [ClusterInstStatusKeys.RESTORING]: {
    key: ClusterInstStatusKeys.RESTORING,
    text: t('重建中'),
    theme: 'loading',
  },
  [ClusterInstStatusKeys.RUNNING]: {
    key: ClusterInstStatusKeys.RUNNING,
    text: t('正常'),
    theme: 'success',
  },
  [ClusterInstStatusKeys.UNAVAILABLE]: {
    key: ClusterInstStatusKeys.UNAVAILABLE,
    text: t('异常'),
    theme: 'danger',
  },
};
export type ClusterInstStatus = `${ClusterInstStatusKeys}`;
