import { t } from '@locales/index';

/**
 * 磁盘类型
 */
export const enum DeviceClass {
  ALL = 'ALL',
  CLOUD_SSD = 'CLOUD_SSD',
  HDD = 'HDD',
  LOCAL_HDD = 'LOCAL_HDD',
  SSD = 'SSD',
}

export const deviceClassDisplayMap = {
  [DeviceClass.ALL]: t('无限制'),
  [DeviceClass.CLOUD_SSD]: t('SSD 云硬盘'),
  [DeviceClass.HDD]: t('普通云硬盘'),
  [DeviceClass.LOCAL_HDD]: t('本地 HDD 硬盘'),
  [DeviceClass.SSD]: t('本地 SSD 硬盘'),
};
