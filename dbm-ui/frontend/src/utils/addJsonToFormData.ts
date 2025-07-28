import _ from 'lodash';

export const addJsonToFormData = (formData: FormData, json: Record<string, any>) => {
  const appendToFormData = (data: any, keyPrefix = '') => {
    _.forEach(data, (value, key) => {
      const currentKey = keyPrefix ? `${keyPrefix}[${key}]` : key;

      if (_.isArray(value)) {
        // 处理数组（包括空数组）
        if (value.length === 0) {
          formData.append(`${currentKey}[]`, ''); // 空数组标记
        } else {
          value.forEach((item, index) => {
            const arrayKey = `${currentKey}[${index}]`;
            if (_.isPlainObject(item) || _.isArray(item)) {
              appendToFormData({ [arrayKey]: item }, '');
            } else {
              formData.append(arrayKey, item);
            }
          });
        }
      } else if (_.isPlainObject(value) && !(value instanceof File)) {
        appendToFormData(value, currentKey); // 递归处理嵌套对象
      } else {
        formData.append(currentKey, value); // 基本类型或 File
      }
    });
  };

  appendToFormData(json);
};
