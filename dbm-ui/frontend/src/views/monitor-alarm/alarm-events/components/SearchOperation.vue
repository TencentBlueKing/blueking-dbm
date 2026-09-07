<template>
  <div class="search-operation-main">
    <BkSelect
      v-model="dbValue"
      class="db-select"
      collapse-tags
      filterable
      :loading="isUserDbaComponentsLoading"
      multiple
      multiple-mode="tag"
      :placeholder="t('请选择DB类型')"
      @change="handleDbSelectChange">
      <BkOption
        v-for="(item, index) in dbList"
        :id="item.id"
        :key="index"
        :name="item.name" />
    </BkSelect>
    <ShieldDateTimePicker
      class="shield-date-picker"
      mode="previous"
      :model-value="filterDateRange"
      @change="handleDateTimeChange"
      @finish="handleDateTimePick" />
    <DbQuickSearch
      v-model="searchValue"
      class="search-select"
      :data="searchSelectData"
      :placeholder="t('搜索告警级别，告警名称，告警内容，告警实例，所属集群…')"
      @change="handleSearchValueChange" />
  </div>
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getUserDbaComponents } from '@services/source/dbadmin';

  import { useBizDbDisplay } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  import ShieldDateTimePicker from '@views/monitor-alarm/common/ShieldDateTimePicker.vue';

  type Emits = (e: 'search', value: Record<string, string>) => void;

  interface Exposes {
    reset: () => void;
  }

  interface Props {
    isGlobalPage: boolean;
    isTodoPage: boolean;
    showBizs?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    showBizs: false,
  });

  const emits = defineEmits<Emits>();

  const route = useRoute();
  const { t } = useI18n();
  const { bizs } = useGlobalBizs();
  const { tabList } = useBizDbDisplay();

  const baseSelectList = [
    {
      id: 'bk_biz_id',
      list: bizs.map((biz) => ({
        label: biz.name,
        value: biz.bk_biz_id,
      })),
      name: t('所属业务'),
      type: 'single',
    },
    {
      id: 'severity',
      list: [
        {
          label: t('提醒'),
          value: 3,
        },
        {
          label: t('预警'),
          value: 2,
        },
        {
          label: t('致命'),
          value: 1,
        },
      ],
      name: t('告警级别'),
      type: 'single',
    },
    {
      id: 'alert_name',
      name: t('告警名称'),
    },
    {
      id: 'description',
      name: t('告警内容'),
    },
    {
      id: 'instance',
      name: t('告警实例'),
    },
    {
      id: 'ip',
      name: t('告警IP'),
      type: 'multiple-input',
    },
    {
      id: 'cluster_domain',
      name: t('所属集群'),
      type: 'multiple-input',
    },
    {
      id: 'stage',
      list: [
        {
          label: t('已通知'),
          value: 'is_handled',
        },
        {
          label: t('已屏蔽'),
          value: 'is_shielded',
        },
        {
          label: t('已流控'),
          value: 'is_blocked',
        },
        {
          label: t('已确认'),
          value: 'is_ack',
        },
      ],
      name: t('处理阶段'),
      type: 'single',
    },
    {
      id: 'status',
      list: [
        {
          label: t('已恢复'),
          value: 'RECOVERED',
        },
        {
          label: t('未恢复'),
          value: 'ABNORMAL',
        },
        {
          label: t('已失效'),
          value: 'CLOSED',
        },
      ],
      name: t('状态'),
      type: 'single',
    },
  ] as QuickSearchProps['data'];

  const dateFormatStr = 'YYYY-MM-DD HH:mm:ss';
  const startTime = dayjs().subtract(7, 'day').format(dateFormatStr);
  const endTime = dayjs().format(dateFormatStr);

  const initSearchValue = () => {
    const baseValue = baseSelectList.reduce<Record<string, string>>((results, item) => {
      const id = route.query[item.id] as string;
      if (id) {
        Object.assign(results, {
          [item.id]: id,
        });
      }
      return results;
    }, {});
    if (!route.query.limit && !route.query.status) {
      Object.assign(baseValue, {
        status: 'ABNORMAL',
      });
    }
    return baseValue;
  };

  const initDatetime = () => {
    const start = route.query.start_time as string;
    const end = route.query.end_time as string;
    if (start && end) {
      return {
        end_time: dayjs(end).format(dateFormatStr),
        start_time: dayjs(start).format(dateFormatStr),
      };
    }

    return {
      end_time: endTime,
      start_time: startTime,
    };
  };

  const initDateRange = initDatetime();

  const filterData = ref<Record<string, any>>(initDateRange);
  const dbValue = ref<string[]>([]);
  const filterDateRange = ref<[string, string]>([initDateRange.start_time, initDateRange.end_time]);
  const searchValue = ref<Record<string, string>>(initSearchValue());

  const searchSelectData = computed(() => {
    const baseSelect = _.cloneDeep(baseSelectList);
    if (!props.showBizs) {
      baseSelect.shift();
    }
    return baseSelect;
  });

  const dbList = computed(() => {
    if (props.isTodoPage) {
      return (userDbaComponents.value?.component || [])
        .filter((item) => DBTypeInfos[item.db_type as DBTypes])
        .map((item) => ({
          id: item.db_type,
          name: item.db_type_display,
        }));
    }
    if (props.isGlobalPage) {
      return Object.values(DBTypeInfos);
    }
    return tabList.value;
  });

  const {
    data: userDbaComponents,
    loading: isUserDbaComponentsLoading,
    run: runGetUserDbaComponents,
  } = useRequest(getUserDbaComponents, {
    manual: true,
  });

  watch(
    () => props.isTodoPage,
    () => {
      if (props.isTodoPage) {
        runGetUserDbaComponents();
      }
    },
    { immediate: true },
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

  const handleDbSelectChange = (value: string[]) => {
    filterData.value.db_types = value;
  };

  const handleDateTimeChange = (value: [string, string]) => {
    filterDateRange.value = value;
  };

  const handleDateTimePick = () => {
    [filterData.value.start_time, filterData.value.end_time] = filterDateRange.value;
  };

  const handleSearchValueChange = (value: Record<string, string>) => {
    if (Object.keys(value).length === 0) {
      filterData.value = {
        db_types: filterData.value.db_types,
        ...initDatetime(),
      };
      return;
    }

    searchSelectData.value.forEach((item) => {
      if (value[item.id] === undefined) {
        delete filterData.value[item.id];
      } else {
        Object.assign(filterData.value, {
          [item.id]: ['bk_biz_id', 'severity'].includes(item.id) ? Number(value[item.id]) : value[item.id],
        });
      }
    });
  };

  defineExpose<Exposes>({
    reset() {
      dbValue.value = [];
      searchValue.value = {
        status: 'ABNORMAL',
      };
      filterData.value = {
        end_time: endTime,
        start_time: startTime,
        status: 'ABNORMAL',
      };
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

    .date-picker {
      width: 308px;
    }

    .search-select {
      width: 450px;
    }

    .shield-date-picker {
      width: 320px !important;
      background: #fff;
    }
  }
</style>
