import { t } from '@locales/index';

/**
 * 特殊选项
 */
export enum SpecialOptions {
  EMPTY = '__empty__',
}

export const specialOptionLabelMap: Record<SpecialOptions, string> = {
  [SpecialOptions.EMPTY]: t('未知'),
};
