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
    <DbQuickSearch
      v-model="searchValue"
      class="search-select"
      :data="searchSelectData"
      parse-url
      :placeholder="t('搜索屏蔽类型')"
      @change="handleSearchValueChange" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

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
      id: 'category',
      list: [
        {
          label: t('基于事件屏蔽'),
          value: 'alert',
        },
        {
          label: t('基于维度屏蔽'),
          value: 'dimension',
        },
        {
          label: t('基于策略屏蔽'),
          value: 'strategy',
        },
      ],
      name: t('屏蔽类型'),
      type: 'single',
    },
  ] as QuickSearchProps['data'];

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
  const searchValue = ref<Record<string, string>>({});

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

  const handleSearchValueChange = (value: Record<string, string>) => {
    if (Object.keys(value).length === 0) {
      filterData.value = initFilterData();
      return;
    }

    Object.assign(filterData.value, value);
  };

  defineExpose<Exposes>({
    reset() {
      filterData.value = {};
      filterDateRange.value = ['', ''];
      searchValue.value = {};
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
