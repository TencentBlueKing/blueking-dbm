<template>
  <div class="inspection-search-box">
    <div class="search-operations">
      <BkDatePicker
        append-to-body
        class="date-picker-main"
        clearable
        :model-value="dateValue"
        @change="handleDatePickerChange" />
      <DbSearchSelect
        class="search-select-main"
        :data="searchData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        unique-select
        @change="handleSearchValueChange" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { ISearchItem, ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getUserList } from '@services/source/user';

  import { useGlobalBizs } from '@stores';

  import { batchSplitRegex } from '@common/regex';

  import { getMenuListSearch } from '@utils';

  interface Props {
    isTodos?: boolean;
    isAssist?: boolean;
    isShowAll?: boolean;
  }

  interface Emits {
    (e: 'change', value: Record<string, any>): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    isTodos: false,
    isAssist: false,
    isShowAll: false,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const dateValue = ref(dayjs().format('YYYY-MM-DD'));
  const searchValue = ref<ISearchValue[]>([]);

  const searchData = computed(() => {
    const bizFilter = {
      name: t('业务'),
      id: 'bk_biz_id',
      children: globalBizsStore.bizs.map((biz) => ({
        id: biz.bk_biz_id,
        name: biz.name,
      })),
    };
    const statusFilter = {
      name: t('状态'),
      id: 'status',
      children: [
        {
          id: 1,
          name: t('正常'),
        },
        {
          id: 0,
          name: t('异常'),
        },
      ],
    };
    const clusterFilter = {
      name: t('集群'),
      id: 'cluster',
      multiple: true,
    };
    const dbaFilter = {
      name: t('主DBA'),
      id: 'dba',
    };
    if (props.isShowAll) {
      return [bizFilter, dbaFilter, clusterFilter, statusFilter] as ISearchItem[];
    }
    if (props.isTodos && !props.isAssist) {
      return [bizFilter, clusterFilter] as ISearchItem[];
    }

    if (props.isTodos && props.isAssist) {
      return [bizFilter, dbaFilter, clusterFilter] as ISearchItem[];
    }

    return [clusterFilter, statusFilter] as ISearchItem[];
  });

  watchEffect(() => {
    if (route.query.create_at__gte && route.query.create_at__lte) {
      dateValue.value = dayjs(route.query.create_at__gte as string).format('YYYY-MM-DD');
    }
  });

  watch(
    () => [searchValue.value, dateValue.value],
    () => {
      const searchObj = searchValue.value.reduce<Record<string, string>>((results, item) => {
        Object.assign(results, {
          [item.id]: item.values?.map((value) => value.id).join(',') || '',
        });
        return results;
      }, {});

      if (dateValue.value) {
        Object.assign(searchObj, {
          create_at__gte: dayjs(dateValue.value).startOf('day').format('YYYY-MM-DD HH:mm:ss'),
          create_at__lte: dayjs(dateValue.value).endOf('day').format('YYYY-MM-DD HH:mm:ss'),
        });
      }
      emits('change', searchObj);
    },
    {
      immediate: true,
    },
  );

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'dba' && keyword) {
      return getMenuListSearch(item, keyword, searchData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchData.value.filter((item) => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'dba') {
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
    return searchData.value.find((set) => set.id === item.id)?.children || [];
  };

  const handleDatePickerChange = (value: string) => {
    dateValue.value = value;
  };

  const handleSearchValueChange = (valueList: ISearchValue[]) => {
    // 防止方法由于searchValue的值改变而被循环触发
    if (JSON.stringify(valueList) === JSON.stringify(searchValue.value)) {
      return;
    }
    // 批量参数统一用,分隔符，展示的分隔符统一成 |
    const handledValueList: ISearchValue[] = [];
    valueList.forEach((item) => {
      if (item.id !== 'cluster') {
        // 原样返回
        handledValueList.push(item);
        return;
      }
      const values = item.values
        ? item.values.reduce(
            (results, value) => {
              const idList = _.uniq(`${value.id.trim()}`.split(batchSplitRegex));
              const nameList = _.uniq(`${value.name.trim()}`.split(batchSplitRegex));
              results.push(
                ...idList.map((id, index) => ({
                  id,
                  name: nameList[index],
                })),
              );
              return results;
            },
            [] as {
              id: string;
              name: string;
            }[],
          )
        : [];

      const searchObj = {
        ...item,
        values,
      };
      handledValueList.push(searchObj);
    });
    searchValue.value = handledValueList;
  };
</script>
<style lang="less">
  .inspection-search-box {
    display: flex;

    .search-operations {
      display: flex;
      gap: 8px;

      .date-picker-main {
        width: 150px;
        margin-right: 8px;
      }

      .search-select-main {
        width: 580px;
      }
    }
  }
</style>
