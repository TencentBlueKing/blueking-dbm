<template>
  <BkQuickSearch
    v-bind="inhertProps"
    v-model="defaultValue"
    clearable
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useRoute } from 'vue-router';

  import BkQuickSearch, { type IValue, type Props } from './bk-quick-search/Index.vue';

  const props = defineProps<
    {
      parseUrl?: boolean;
    } & Props
  >();

  const emits = defineEmits<(e: 'change', value: Record<string, string>, payload: IValue[]) => void>();

  const modelValue = defineModel<Record<string, string>>({});

  const route = useRoute();

  const defaultValue = shallowRef<IValue[]>([]);

  const inhertProps = computed(() => {
    const baseProps = { ...props };
    delete baseProps['modelValue'];
    // @ts-expect-error 删除不存在的 props
    delete baseProps['parseUrl'];
    return baseProps;
  });

  const formatResult = (data: IValue[]) => {
    return data.reduce<Record<string, string>>((result, item) => {
      const currentDataConfig = _.find(props.data, (config) => config.id === item.id)!;
      if (currentDataConfig.type === 'date-range' || currentDataConfig.type === 'datetime-range') {
        Object.assign(result, {
          [`${currentDataConfig.id}__gte`]: item.values[0].value,
          [`${currentDataConfig.id}__lte`]: item.values[1].value,
          [`${currentDataConfig.id}`]: `${item.values[0].value},${item.values[1].value}`,
        });
      } else if (currentDataConfig.type === 'multiple' || currentDataConfig.type === 'multiple-cascader') {
        Object.assign(result, {
          [currentDataConfig.id]: item.values.map((value) => value.value),
        });
      } else {
        Object.assign(result, {
          [currentDataConfig.id]: item.values.map((value) => value.value).join(','),
        });
      }

      return result;
    }, {});
  };

  if (props.parseUrl) {
    const routeQuery = route.query;

    modelValue.value = props.data.reduce((result, configItem) => {
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
  }

  let isInnerSelfChange = false;
  watch(
    modelValue,
    _.throttle(
      () => {
        const latestValue = modelValue.value;
        if (!latestValue) {
          return;
        }
        if (isInnerSelfChange) {
          isInnerSelfChange = false;
          return;
        }

        console.log('from watch modelVale ', latestValue);

        const taskQueue = props.data.map((searchItemConfig) => {
          // 解析时间
          if (
            latestValue[searchItemConfig.id] &&
            (searchItemConfig.type === 'date-range' || searchItemConfig.type === 'datetime-range')
          ) {
            const [startTime, endTime] = latestValue[searchItemConfig.id].split(',');
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
                return searchItemConfig.remoteMethod();
              }
              if (_.isArray(searchItemConfig.list)) {
                return searchItemConfig.list;
              }
              return [];
            })
            .then((data) => {
              // 备选数据结构
              // 级联
              if (data.length > 0 && _.isArray(data[0].children)) {
                return data.reduce((result, item) => result.concat(item.children || []), [] as IValue['values']);
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
                values: _.filter((latestValue[searchItemConfig.id] as string).split(','), (item) =>
                  Boolean(_.trim(item)),
                ).map((text) => ({
                  label: data[text] ? data[text] : text,
                  value: text,
                })),
              };
            });
        });
        Promise.all(taskQueue).then((data) => {
          console.log('defaultValue = ', data);
          defaultValue.value = _.filter(data, (item) => Boolean(item)) as IValue[];
          handleChange(defaultValue.value);
        });
      },
      60,
      {
        leading: false,
        trailing: true,
      },
    ),
    {
      immediate: true,
    },
  );

  const handleChange = (value: IValue[]) => {
    isInnerSelfChange = true;
    const result = formatResult(value);
    console.log('handleChange ==== ', value, result);

    modelValue.value = result;
    emits('change', result, value);
  };
</script>
