import { comType } from '../constants';
import type { IValue, Props } from '../Index.vue';

export const getValuesText = (values: IValue['values'], config?: Props['data'][number]) => {
  if (config && config.type && [comType.DATE_RANGE, comType.DATETIME_RANGE].includes(config.type as comType)) {
    return `${values[0].label} ~ ${values[1].label}`;
  }

  return values.map((item) => item.label).join(' | ');
};
