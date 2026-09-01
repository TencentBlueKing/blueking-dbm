<template>
  <BkQuickSearch
    v-bind="inheritProps"
    v-model="defaultValue"
    clearable
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useRoute } from 'vue-router';

  import BkQuickSearch, {
    type IValue,
    type Props as QuickSearchProps,
  } from '@components/db-quick-search/bk-quick-search/Index.vue';

  const props = defineProps<
    {
      parseUrl?: boolean;
    } & QuickSearchProps
  >();

  const emits = defineEmits<(e: 'change', value: Record<string, string>, payload: IValue[]) => void>();

  const modelValue = defineModel<Record<string, any>>({});

  const route = useRoute();

  const defaultValue = shallowRef<IValue[]>([]);

  const inheritProps = computed(() => _.omit(props, 'parseUrl'));

  const parseCascaderValues = (item: IValue) => {
    const parseValue = (value: string) => {
      // important: 优化分割符
      const splitCode = '#';
      if (value.includes(splitCode)) {
        return value.split(splitCode) as [string, string];
      }
      return [item.id, value] as [string, string];
    };

    const keyValueMap: Record<string, string[]> = {};
    item.values.forEach((valueItem) => {
      const [key, value] = parseValue(`${valueItem.value}`);
      if (!keyValueMap[key]) {
        keyValueMap[key] = [];
      }
      keyValueMap[key].push(value);
    });
    return Object.entries(keyValueMap).reduce(
      (result, [key, value]) => {
        return Object.assign(result, {
          [key]: value.join(','),
        });
      },
      {} as Record<string, string>,
    );
  };

  const formatResult = (data: IValue[]) => {
    return data.reduce<Record<string, string>>((result, item) => {
      // 搜索项配置可能已经被外部移除，此时按默认方式透传值，保证搜索条件不丢失
      const configType = _.find(props.data, (config) => config.id === item.id)?.type;
      if ((configType === 'date-range' || configType === 'datetime-range') && item.values.length > 1) {
        Object.assign(result, {
          [`${item.id}__gte`]: item.values[0]!.value,
          [`${item.id}__lte`]: item.values[1]!.value,
          [`${item.id}`]: `${item.values[0]!.value},${item.values[1]!.value}`,
        });
      } else if (configType === 'cascader' || configType === 'multiple-cascader') {
        Object.assign(result, {
          [item.id]: item.values.map((value) => value.value).join(','),
          ...parseCascaderValues(item),
        });
      } else {
        Object.assign(result, {
          [item.id]: item.values.map((value) => value.value).join(','),
        });
      }

      return result;
    }, {});
  };

  if (props.parseUrl) {
    const routeQuery = route.query;

    const urlCache = props.data.reduce((result, configItem) => {
      if (routeQuery[`${configItem.id}__gte`] && routeQuery[`${configItem.id}__lte`]) {
        Object.assign(result, {
          [`${configItem.id}__gte`]: routeQuery[`${configItem.id}__gte`],
          [`${configItem.id}__lte`]: routeQuery[`${configItem.id}__lte`],
        });
      }
      if (routeQuery[configItem.id]) {
        const realValue = _.filter((routeQuery[configItem.id] as string)!.split(','), (item) => Boolean(_.trim(item)));
        if (realValue.length > 0) {
          Object.assign(result, {
            [configItem.id]: routeQuery[configItem.id],
          });
        }
      }
      return result;
    }, {});
    if (Object.keys(urlCache).length > 0) {
      modelValue.value = urlCache;
    }
  }

  // 记录最近一次向外输出的值，用于识别组件自身的回写，避免和外部赋值互相覆盖
  let lastOutputValue: Record<string, string> | undefined;
  const handleModelValueChange = _.throttle(
    () => {
      const latestValue = modelValue.value;
      if (!latestValue) {
        return;
      }
      if (lastOutputValue && _.isEqual(latestValue, lastOutputValue)) {
        return;
      }

      const taskQueue = props.data.map((searchItemConfig) => {
        // 解析时间
        if (
          latestValue[searchItemConfig.id] &&
          (searchItemConfig.type === 'date-range' || searchItemConfig.type === 'datetime-range')
        ) {
          const [startTime, endTime] = latestValue[searchItemConfig.id]!.split(',');
          return Promise.resolve().then(() => {
            return {
              id: searchItemConfig.id,
              name: searchItemConfig.name,
              values: [
                {
                  label: startTime,
                  value: startTime,
                },
                {
                  label: endTime,
                  value: endTime,
                },
              ],
            };
          });
        }
        // 不支持的 key
        if (!latestValue[searchItemConfig.id]) {
          return Promise.resolve(null);
        }
        // 备选
        return Promise.resolve()
          .then(() => {
            // 备选数据来源
            if (_.isFunction(searchItemConfig.remoteMethod)) {
              return searchItemConfig.remoteMethod({ defaultValue: latestValue[searchItemConfig.id] });
            }
            if (_.isArray(searchItemConfig.list)) {
              return searchItemConfig.list;
            }
            return [];
          })
          .then((data) => {
            // 备选数据结构
            // 级联
            if (
              data.length > 0 &&
              (searchItemConfig.type === 'cascader' || searchItemConfig.type === 'multiple-cascader')
            ) {
              const result: { label: string; value: string | number }[] = [];
              data.forEach((parentItem) => {
                result.push({
                  label: parentItem.label,
                  value: parentItem.value,
                });
                (parentItem.children || []).forEach((childItem) => {
                  result.push({
                    label: searchItemConfig.props?.showAllLevels
                      ? `${parentItem.label}/${childItem.label}`
                      : childItem.label,
                    value: childItem.value,
                  });
                });
              });
              return result;
            }
            return data;
          })
          .then((data) => {
            // 备选数据 value: label 映射
            return data.reduce<Record<string, string>>((result, item) => {
              return Object.assign(result, {
                [`${item.value}`]: item.label,
              });
            }, {});
          })
          .then((data) => {
            // 数据回填
            return {
              id: searchItemConfig.id,
              name: searchItemConfig.name,
              values: _.filter(String(latestValue[searchItemConfig.id]).split(','), (item) =>
                Boolean(_.trim(item)),
              ).map((text) => ({
                label: data[text] ? data[text] : text,
                value: text,
              })),
            };
          });
      });
      Promise.all(taskQueue).then((data) => {
        defaultValue.value = _.filter(data, (item) => Boolean(item)) as IValue[];
        handleChange(defaultValue.value);
      });
    },
    60,
    {
      leading: false,
      trailing: true,
    },
  );

  // 外部可能就地修改筛选对象，需要深度监听才能回显
  watch(modelValue, handleModelValueChange, {
    deep: true,
    immediate: true,
  });

  onBeforeUnmount(() => {
    handleModelValueChange.cancel();
  });

  const handleChange = (value: IValue[]) => {
    const result = formatResult(value);

    lastOutputValue = result;
    modelValue.value = result;
    emits('change', result, value);
  };
</script>
