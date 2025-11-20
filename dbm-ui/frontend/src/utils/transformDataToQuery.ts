export const transfromDataToQuery = (data: Record<string, string | number | string[] | number[]>) => {
  return Object.keys(data).reduce((result, key) => {
    const value = data[key];
    if (value) {
      Object.assign(result, {
        [key]: Array.isArray(value) ? value.join(',') : value,
      });
    }
    return result;
  }, {});
};
