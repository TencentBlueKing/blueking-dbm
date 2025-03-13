<template>
  <div class="search-operation-main">
    <ShieldDateTimePicker
      class="shield-date-picker"
      clearable
      :model-value="filterDateRange"
      :placeholder="t('搜索屏蔽开始时间')"
      @change="handleDateTimeChange"
      @finish="handleDateTimePick" />
    <DbSearchSelect
      v-model="searchValue"
      class="search-select"
      :data="searchSelectData"
      :get-menu-list="getMenuList"
      :placeholder="t('搜索屏蔽类型')"
      unique-select
      @change="handleSearchValueChange" />
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem, ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import { getUserList } from '@services/source/user';

  import ShieldDateTimePicker from '@views/monitor-alarm/common/ShieldDateTimePicker.vue';

  import { getMenuListSearch } from '@utils';

  type Emits = (e: 'search', value: Record<string, string>) => void;

  interface Exposes {
    reset: () => void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const filterData = ref<Record<string, string>>({});
  const filterDateRange = ref<[string, string]>(['', '']);
  const searchValue = ref<ISearchValue[]>([]);

  const searchSelectData = computed(
    () =>
      [
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
            // {
            //   id: 'scope',
            //   name: t('基于主机屏蔽'),
            // },
            {
              id: 'strategy',
              name: t('基于策略屏蔽'),
            },
          ],
          id: 'category',
          name: t('屏蔽类型'),
        },
      ] as ISearchItem[],
  );

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

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'updator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchSelectData.value.filter((item) => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'updator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then((res) =>
        res.results.map((item) => ({
          id: item.username,
          name: item.username,
        })),
      );
    }

    // 不需要远层加载
    return searchSelectData.value.find((set) => set.id === item.id)?.children || [];
  };

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
      filterData.value = {
        time_range: filterData.value.time_range,
      };
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
