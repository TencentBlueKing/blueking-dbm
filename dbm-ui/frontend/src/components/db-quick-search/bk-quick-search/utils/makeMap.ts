export const makeMap = (list: Array<string | number> = []): Record<string | number, boolean> => {
  const map = Object.create(null);
  list.forEach((item) => {
    map[item] = true;
  });
  return map;
};
