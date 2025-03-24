<template>
  <div class="search-operation-main">
    <BkSelect
      v-model="dbValue"
      class="db-select"
      collapse-tags
      filterable
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
    <DbSearchSelect
      class="search-select"
      :data="searchSelectData"
      :model-value="searchValue"
      :parse-url="false"
      :placeholder="t('搜索告警级别，告警名称，告警内容，告警实例，所属集群…')"
      unique-select
      @change="handleSearchValueChange" />
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem, ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import ShieldDateTimePicker from '@views/monitor-alarm/common/ShieldDateTimePicker.vue';

  type Emits = (e: 'search', value: Record<string, string>) => void;

  interface Exposes {
    reset: () => void;
  }

  interface Props {
    showBizs?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    showBizs: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();
  const route = useRoute();

  const baseSelectList = [
    {
      children: bizs.map((biz) => ({
        id: biz.bk_biz_id,
        name: biz.name,
      })),
      id: 'bk_biz_id',
      name: t('所属业务'),
    },
    {
      children: [
        {
          id: 3,
          name: t('提醒'),
        },
        {
          id: 2,
          name: t('预警'),
        },
        {
          id: 1,
          name: t('致命'),
        },
      ],
      id: 'severity',
      name: t('告警级别'),
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
    },
    {
      id: 'cluster_domain',
      name: t('所属集群'),
    },
    {
      children: [
        {
          id: 'is_handled',
          name: t('已通知'),
        },
        {
          id: 'is_shielded',
          name: t('已屏蔽'),
        },
        {
          id: 'is_blocked',
          name: t('已流控'),
        },
        {
          id: 'is_ack',
          name: t('已确认'),
        },
      ],
      id: 'stage',
      name: t('处理阶段'),
    },
    {
      children: [
        {
          id: 'RECOVERED',
          name: t('已恢复'),
        },
        {
          id: 'ABNORMAL',
          name: t('未恢复'),
        },
        {
          id: 'CLOSED',
          name: t('已失效'),
        },
      ],
      id: 'status',
      name: t('状态'),
    },
  ];

  const dbList = Object.values(DBTypeInfos);
  const dateFormatStr = 'YYYY-MM-DD HH:mm:ss';
  const startTime = dayjs().subtract(7, 'day').format(dateFormatStr);
  const endTime = dayjs().format(dateFormatStr);

  const defaultStatus = {
    id: 'status',
    name: t('状态'),
    values: [
      {
        id: 'ABNORMAL',
        name: t('未恢复'),
      },
    ],
  };

  let isInit = true;

  const initSearchValue = () => {
    const baseValue = baseSelectList.reduce<ISearchValue[]>((results, item) => {
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
              id: item.id === 'bk_biz_id' ? Number(id) : id,
              name,
            },
          ],
        });
      }
      return results;
    }, []);
    if (!route.query.limit && !route.query.status) {
      baseValue.push(defaultStatus);
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
  const searchValue = ref<ISearchValue[]>(initSearchValue());

  const searchSelectData = computed(() => {
    const baseSelect = _.cloneDeep(baseSelectList);
    if (!props.showBizs) {
      baseSelect.shift();
    }
    return baseSelect as ISearchItem[];
  });

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

  const handleSearchValueChange = (valueList: ISearchValue[]) => {
    // 防止方法由于searchValue的值改变而被循环触发
    if (!isInit && JSON.stringify(valueList) === JSON.stringify(searchValue.value)) {
      return;
    }
    isInit = false;
    const handledValueList: ISearchValue[] = [];
    valueList.forEach((item) => {
      if (!['cluster_domain', 'ip'].includes(item.id)) {
        handledValueList.push(item);
        return;
      }
      const values = item.values
        ? [
            {
              id: item.values[0].id.split(batchSplitRegex).join(','),
              name: item.values[0].name.split(batchSplitRegex).join(' | '),
            },
          ]
        : [];

      const searchObj = {
        ...item,
        values,
      };
      handledValueList.push(searchObj);
    });

    searchValue.value = handledValueList;

    if (!handledValueList.length) {
      filterData.value = {
        db_types: filterData.value.db_types,
        ...initDatetime(),
      };
      return;
    }
    const handledValueMap = handledValueList.reduce<Record<string, ISearchValue>>((results, item) => {
      Object.assign(results, {
        [item.id]: item,
      });
      return results;
    }, {});
    searchSelectData.value.forEach((item) => {
      const targetItem = handledValueMap[item.id];
      if (!targetItem) {
        delete filterData.value[item.id];
      } else {
        Object.assign(filterData.value, {
          [item.id]:
            targetItem.values!.length > 1 ? targetItem.values!.map((value) => value.id) : targetItem.values![0].id,
        });
      }
    });
  };

  defineExpose<Exposes>({
    reset() {
      dbValue.value = [];
      searchValue.value = [defaultStatus];
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
