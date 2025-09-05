import { comType } from '@components/db-quick-search/bk-quick-search/constants';
import type { Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const calcNeedShowValueMenu = (data: Props['data'][number]) => {
  return (data.type && data.type !== comType.INPUT && data.type !== comType.MULTIPLE_INPUT) || data.component;
};
