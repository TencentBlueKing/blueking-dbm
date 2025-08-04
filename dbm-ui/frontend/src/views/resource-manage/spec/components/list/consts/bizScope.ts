import { t } from '@locales/index';

/**
 * 应用范围
 */
export enum BizScopes {
  ALL = 'ALL',
  BIZ = 'BIZ',
}

export const BizScopesInfoMap = {
  [BizScopes.ALL]: {
    icon: 'quanbu',
    label: t('全部业务'),
  },
  [BizScopes.BIZ]: {
    icon: 'bufenkejian',
    label: t('指定业务'),
  },
};

export const BizScopesInfoList = Object.entries(BizScopesInfoMap).map(([key, info]) => ({
  id: key,
  ...info,
}));
