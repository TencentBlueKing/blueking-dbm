<template>
  <div class="inspection-search-operations">
    <BkCheckbox
      v-if="showOnlyAbnormal"
      v-model="isOnlyAbnormal">
      {{ t('仅显示预警 / 异常') }}
    </BkCheckbox>
    <BkDatePicker
      append-to-body
      class="date-picker-main"
      clearable
      :model-value="dateValue"
      @change="handleDatePickerChange" />
    <DbQuickSearch
      v-model="searchValue"
      class="search-select-main"
      :data="searchData"
      unique-select
      value-split-code="," />
  </div>
</template>
<script setup lang="ts">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { getUserList } from '@services/source/user';

  import { useGlobalBizs } from '@stores';

  import DbQuickSearch from '@components/db-quick-search/Index.vue';

  interface Props {
    isAssist?: boolean;
    isShowAll?: boolean;
    isTodos?: boolean;
    showOnlyAbnormal?: boolean;
  }

  type Emits = (e: 'change', value: Record<string, any>) => void;

  const props = withDefaults(defineProps<Props>(), {
    isAssist: false,
    isShowAll: false,
    isTodos: false,
    showOnlyAbnormal: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const isOnlyAbnormal = ref(true);
  const dateValue = ref(dayjs().format('YYYY-MM-DD'));
  const searchValue = ref<Record<string, any>>({});

  const searchData = computed<ComponentProps<typeof DbQuickSearch>['data']>(() => {
    const bizFilter = {
      id: 'bk_biz_id',
      list: globalBizsStore.bizs.map((biz) => ({
        label: biz.name,
        value: biz.bk_biz_id,
      })),
      name: t('业务'),
      type: 'single',
    };
    const statusFilter = {
      id: 'state',
      list: [
        {
          label: t('正常'),
          value: 'normal',
        },
        {
          label: t('异常'),
          value: 'abnormal',
        },
        {
          label: t('预警'),
          value: 'warning',
        },
      ],
      name: t('状态'),
      type: 'single',
    };
    if (isOnlyAbnormal.value) {
      statusFilter.list.splice(0, 1);
    }
    const clusterFilter = {
      id: 'cluster',
      name: t('集群'),
    };
    const dbaFilter = {
      id: 'dba',
      name: t('主DBA'),
      remoteMethod: requestUserList,
      remoteSearch: true,
      type: 'single',
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

  watch(
    () => [searchValue.value, dateValue.value, isOnlyAbnormal.value],
    () => {
      const searchObj = _.cloneDeep(searchValue.value);
      if (dateValue.value) {
        Object.assign(searchObj, {
          create_at__gte: dayjs(dateValue.value).startOf('day').format('YYYY-MM-DD HH:mm:ss'),
          create_at__lte: dayjs(dateValue.value).endOf('day').format('YYYY-MM-DD HH:mm:ss'),
        });
      }

      Object.assign(searchObj, {
        isOnlyAbnormal: isOnlyAbnormal.value,
      });
      emits('change', searchObj);
    },
    {
      immediate: true,
    },
  );

  const initSearchSelect = () => {
    if (route.query.create_at__gte && route.query.create_at__lte) {
      dateValue.value = dayjs(route.query.create_at__gte as string).format('YYYY-MM-DD');
    }
    if (route.query.isOnlyAbnormal) {
      isOnlyAbnormal.value = route.query.isOnlyAbnormal === 'true';
    }

    ['bk_biz_id', 'cluster', 'dba', 'state'].forEach((item) => {
      if (route.query[item]) {
        searchValue.value[item] = route.query[item];
      }
    });
  };

  const requestUserList = (params: { defaultValue?: string; keyword?: string }) => {
    const requestParams = {};
    if (params.defaultValue) {
      Object.assign(requestParams, { exact_lookups: params.defaultValue });
    }
    if (params.keyword) {
      Object.assign(requestParams, { fuzzy_lookups: params.keyword });
    }

    return getUserList(requestParams).then((data) =>
      data.results.map((item) => ({
        label: `${item.username} (${item.display_name})`,
        value: item.username,
      })),
    );
  };

  const handleDatePickerChange = (value: string) => {
    dateValue.value = value;
  };

  initSearchSelect();
</script>
<style lang="less">
  .inspection-search-operations {
    display: flex;
    gap: 8px;

    .date-picker-main {
      width: 150px;
    }

    .search-select-main {
      width: 580px;
    }
  }
</style>
