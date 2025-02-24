import isDate from 'lodash/isDate';
import isEmpty from 'lodash/isEmpty';

export default {
  email: (value: string): boolean => /^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$/.test(value),
  max: (value: number, max: number): boolean => max >= value,
  maxlength: (value: string, maxlength: number): boolean => value.length <= maxlength,
  min: (value: number, min: number): boolean => value >= min,
  pattern: (value: string, pattern: RegExp): boolean => {
    const result = pattern.test(value);
    pattern.lastIndex = 0; // eslint-disable-line no-param-reassign
    return result;
  },
  required: (value: any): boolean => {
    if (typeof value === 'number' || typeof value === 'boolean' || isDate(value)) {
      return true;
    }
    return !isEmpty(value);
  },
};
