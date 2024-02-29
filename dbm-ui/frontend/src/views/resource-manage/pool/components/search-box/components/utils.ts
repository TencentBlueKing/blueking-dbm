import _ from 'lodash';

export const isValueEmpty = (value: any) =>
  (Array.isArray(value) && (value.length < 1 || _.filter(value, (item) => item !== '').length < 1)) || value === '';
