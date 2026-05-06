import _ from 'lodash';

/**
 * 验证字符串是否为合法 JSON
 * @param jsonString 要验证的字符串
 * @returns 是否为合法 JSON
 */
export const isValidJSON = (jsonString: string): boolean => {
  if (typeof jsonString !== 'string') {
    return false;
  }

  try {
    const result = JSON.parse(jsonString);
    // 确保解析后不是基本类型，除非是 null（JSON 允许 null）
    const type = typeof result;
    const isValid = result === null || type === 'object' || _.isArray(result);
    return isValid;
  } catch {
    return false;
  }
};
