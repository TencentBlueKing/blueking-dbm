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

/**
 * K8S集群实例状态
 */
export enum ClusterK8sInstStatusKeys {
  FAILED = 'Failed',
  PENDING = 'Pending',
  RUNNING = 'Running',
}
export const clusterK8sInstStatus = {
  [ClusterK8sInstStatusKeys.FAILED]: {
    icon: 'abnormal',
    key: ClusterK8sInstStatusKeys.FAILED,
    text: t('失败'),
  },
  [ClusterK8sInstStatusKeys.PENDING]: {
    icon: 'sync-pending',
    key: ClusterK8sInstStatusKeys.PENDING,
    text: t('等待调度'),
  },
  [ClusterK8sInstStatusKeys.RUNNING]: {
    icon: 'normal',
    key: ClusterK8sInstStatusKeys.RUNNING,
    text: t('运行中'),
  },
};
export type ClusterK8sInstStatus = `${ClusterK8sInstStatusKeys}`;
