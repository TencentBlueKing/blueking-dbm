import type { SearchSelect } from 'bkui-vue';
import _ from 'lodash';

type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];

export const getSearchSelectValue = (
  data: NonNullable<SearchSelectProps['data']>,
  urlPayload: Record<string, string>,
) => {
  const defaultValue: SearchSelectProps['modelValue'] = [];

  data.forEach((item) => {
    if (_.has(urlPayload, item.id)) {
      const searchValue = urlPayload[item.id];
      const childNameMap = (item.children || []).reduce<Record<string, string>>(
        (result, item) => Object.assign(result, { [item.id]: item.name }),
        {},
      );

      defaultValue.push({
        ...item,
        values: item.multiple
          ? searchValue.split(',').map((item) => ({ id: item, name: childNameMap[item] ?? item }))
          : [{ id: searchValue, name: childNameMap[searchValue] ?? searchValue }],
      });
    }
  });
  // 保留初始化时传入的 modelValues
  return defaultValue.length > 0 ? defaultValue : [];
};
