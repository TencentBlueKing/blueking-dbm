import { t } from '@/locales/index';

/** 数据库配置层级 */
export enum ConfLevels {
  PLAT = 'plat',
  APP = 'app',
  MODULE = 'module',
  CLUSTER = 'cluster',
}
export type ConfLevelValues = `${ConfLevels}`;

/** 数据库配置层级信息 */
export const confLevelInfos = {
  [ConfLevels.PLAT]: {
    id: ConfLevels.PLAT,
    lockText: t('平台锁定'),
    tagText: t('平台配置'),
  },
  [ConfLevels.APP]: {
    id: ConfLevels.APP,
    lockText: t('业务锁定'),
    tagText: t('业务配置'),
  },
  [ConfLevels.MODULE]: {
    id: ConfLevels.MODULE,
    lockText: t('模块锁定'),
    tagText: t('模块配置'),
  },
  [ConfLevels.CLUSTER]: {
    id: ConfLevels.CLUSTER,
    lockText: t('集群锁定'),
    tagText: t('集群配置'),
  },
};
