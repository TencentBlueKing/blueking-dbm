import { t } from '@locales/index';

export enum Affinity {
  CROS_SUBZONE = 'CROS_SUBZONE',
  CROSS_RACK = 'CROSS_RACK',
  CROSS_SUBZONE_STRONG = 'CROSS_SUBZONE_STRONG', // mongodb 特有
  CROSS_SUBZONE_WEAK = 'CROSS_SUBZONE_WEAK', // mongodb 特有
  MAX_EACH_ZONE_EQUAL = 'MAX_EACH_ZONE_EQUAL',
  NONE = 'NONE',
  SAME_SUBZONE_CROSS_SWTICH = 'SAME_SUBZONE_CROSS_SWTICH',
}

export const affinityMap: {
  [x in Affinity]?: string;
} = {
  [Affinity.CROS_SUBZONE]: t('跨园区'),
  [Affinity.CROSS_RACK]: t('跨机架'),
  [Affinity.MAX_EACH_ZONE_EQUAL]: t('尽量分散'),
  [Affinity.NONE]: t('无'),
  [Affinity.SAME_SUBZONE_CROSS_SWTICH]: t('指定园区'),
  // SAME_SUBZONE: t('同城同园区'), // 弃用
};

export const mongodbAffinityMap: {
  [x in Affinity]?: string;
} = {
  [Affinity.CROSS_RACK]: t('跨机架'),
  [Affinity.CROSS_SUBZONE_STRONG]: t('跨园区（强）'),
  [Affinity.CROSS_SUBZONE_WEAK]: t('跨园区（弱）'),
  [Affinity.NONE]: t('无'),
  [Affinity.SAME_SUBZONE_CROSS_SWTICH]: t('指定园区'),
};
