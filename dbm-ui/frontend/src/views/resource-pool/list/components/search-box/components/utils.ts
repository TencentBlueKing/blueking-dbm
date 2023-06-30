import _ from 'lodash';

export const isValueEmpty = (value: any) => (
  Array.isArray(value) && (value.length < 1 || _.filter(value, _ => _).length < 1)
)
|| value === '';
