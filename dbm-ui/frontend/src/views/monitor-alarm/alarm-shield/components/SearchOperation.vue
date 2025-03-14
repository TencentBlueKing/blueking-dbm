<template>
  <div class="search-operation-main">
    <ShieldDateTimePicker
      class="shield-date-picker"
      clearable
      mode="previous"
      :model-value="filterDateRange"
      :placeholder="t('搜索屏蔽开始时间')"
      @change="handleDateTimeChange"
      @finish="handleDateTimePick" />
    <DbSearchSelect
      v-model="searchValue"
      class="search-select"
      :data="searchSelectData"
      :placeholder="t('搜索屏蔽类型')"
      unique-select
      @change="handleSearchValueChange" />
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem, ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import ShieldDateTimePicker from '@views/monitor-alarm/common/ShieldDateTimePicker.vue';

  type Emits = (e: 'search', value: Record<string, string>) => void;

  interface Exposes {
    reset: () => void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();

  const searchSelectData = [
    {
      children: [
        {
          id: 'alert',
          name: t('基于事件屏蔽'),
        },
        {
          id: 'dimension',
          name: t('基于维度屏蔽'),
        },
        {
          id: 'strategy',
          name: t('基于策略屏蔽'),
        },
      ],
      id: 'category',
      name: t('屏蔽类型'),
    },
  ] as ISearchItem[];

  const initSearchValue = () =>
    searchSelectData.reduce<ISearchValue[]>((results, item) => {
      const id = route.query[item.id] as string;
      if (id) {
        let name = id;
        if (item.children) {
          const targetName = item.children.find((child) => child.id === id)?.name;
          if (targetName) {
            name = targetName;
          }
        }
        results.push({
          ...item,
          values: [
            {
              id,
              name,
            },
          ],
        });
      }
      return results;
    }, []);

  const initDatetime = () => {
    const timeStr = route.query.time_range as string;
    if (timeStr) {
      const [start, end] = timeStr.split('--');
      return [start, end] as [string, string];
    }

    return ['', ''];
  };

  const initDateRange = initDatetime();

  const initFilterData = (): Record<string, string> => {
    if (initDateRange.every((item) => !!item)) {
      return {
        time_range: `${initDateRange[0]}--${initDateRange[1]}`,
      };
    }

    return {};
  };

  const filterData = ref<Record<string, string>>(initFilterData());
  const filterDateRange = ref<[string, string]>([initDateRange[0], initDateRange[1]]);
  const searchValue = ref<ISearchValue[]>(initSearchValue());

  watch(
    filterData,
    () => {
      emits('search', filterData.value);
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleDateTimeChange = (value: [string, string]) => {
    filterDateRange.value = value;
    if (value.every((item) => !item)) {
      delete filterData.value.time_range;
    }
  };

  const handleDateTimePick = () => {
    filterData.value.time_range =
      filterDateRange.value.length > 0 ? `${filterDateRange.value[0]}--${filterDateRange.value[1]}` : '';
  };

  const handleSearchValueChange = (valueList: ISearchValue[]) => {
    if (!valueList.length) {
      filterData.value = initFilterData();
      return;
    }

    const searchData = valueList.reduce<Record<string, string>>((results, item) => {
      Object.assign(results, {
        [item.id]: item.values!.map((value) => value.id).join(','),
      });
      return results;
    }, {});
    Object.assign(filterData.value, searchData);
  };

  defineExpose<Exposes>({
    reset() {
      filterData.value = {};
      filterDateRange.value = ['', ''];
      searchValue.value = [];
    },
  });
</script>
<style lang="less" scoped>
  .search-operation-main {
    display: flex;
    justify-content: flex-end;
    gap: 8px;

    .db-select {
      width: 290px;
    }

    .shield-date-picker {
      width: 320px !important;
      background: #fff;
    }

    .search-select {
      width: 440px;
    }
  }
</style>
