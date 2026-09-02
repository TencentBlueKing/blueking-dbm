import dayjs from 'dayjs';
import { useRequest } from 'vue-request';

import { getUserDbaComponents } from '@services/source/dbadmin';

import { useBizDbDisplay } from '@hooks';

import { useGlobalBizs } from '@stores';

import { DBTypeInfos, DBTypes } from '@common/const';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
import SingleSelect from '@components/db-table/components/SingleSelect.vue';

import { t } from '@/locales';

// 这两项的值不能原样下发给接口：db_types 只接受数组，时间范围要拆成 start_time / end_time
export const dbTypeSearchId = 'db_types';
export const timeRangeSearchId = 'time_range';

const dateFormatStr = 'YYYY-MM-DD HH:mm:ss';

// 处理阶段、状态选项，快捷搜索与表头筛选共用
const stageList = [
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
];

const statusList = [
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
];

// 与原 ShieldDateTimePicker 的 previous 模式保持一致的快捷选项
const timeRangeShortcuts: { text: string; value: () => [Date, Date] }[] = [
  {
    text: t('近n分钟', { n: 30 }),
    value: () => [dayjs().subtract(30, 'minute').toDate(), dayjs().toDate()],
  },
  {
    text: t('近1小时'),
    value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
  },
  {
    text: t('近n小时', { n: 12 }),
    value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
  },
  {
    text: t('近1天'),
    value: () => [dayjs().subtract(1, 'day').toDate(), dayjs().toDate()],
  },
  {
    text: t('近n天', { n: 7 }),
    value: () => [dayjs().subtract(7, 'day').toDate(), dayjs().toDate()],
  },
  {
    text: t('近1个月'),
    value: () => [dayjs().subtract(1, 'month').toDate(), dayjs().toDate()],
  },
  {
    text: t('近n个月', { n: 3 }),
    value: () => [dayjs().subtract(3, 'month').toDate(), dayjs().toDate()],
  },
  {
    text: t('近n个月', { n: 6 }),
    value: () => [dayjs().subtract(6, 'month').toDate(), dayjs().toDate()],
  },
];

export const useQuickSearch = (options: { isGlobalPage: ComputedRef<boolean>; isTodoPage: ComputedRef<boolean> }) => {
  const route = useRoute();
  const { bizs } = useGlobalBizs();
  const { tabList } = useBizDbDisplay();

  // 接口的 start_time / end_time 必填，未指定时默认查近 7 天
  const defaultStartTime = dayjs().subtract(7, 'day').format(dateFormatStr);
  const defaultEndTime = dayjs().format(dateFormatStr);

  // 告警级别由页面左上角的筛选条负责，不重复放进快捷搜索
  const baseSelectList = [
    {
      id: timeRangeSearchId,
      name: t('告警产生时间'),
      props: {
        shortcuts: timeRangeShortcuts,
      },
      type: 'datetime-range',
    },
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
      list: stageList,
      name: t('处理阶段'),
      type: 'single',
    },
    {
      id: 'status',
      list: statusList,
      name: t('状态'),
      type: 'single',
    },
  ] as QuickSearchProps['data'];

  const { data: userDbaComponents, run: runGetUserDbaComponents } = useRequest(getUserDbaComponents, {
    manual: true,
  });

  const dbList = computed(() => {
    if (options.isTodoPage.value) {
      return (userDbaComponents.value?.component || [])
        .filter((item) => DBTypeInfos[item.db_type as DBTypes])
        .map((item) => ({
          label: item.db_type_display,
          value: item.db_type,
        }));
    }

    const dbTypeInfoList = options.isGlobalPage.value ? Object.values(DBTypeInfos) : tabList.value;

    return dbTypeInfoList.map((item) => ({
      label: item.name,
      value: item.id as string,
    }));
  });

  const quickSearchData = computed(
    () =>
      [
        {
          id: dbTypeSearchId,
          list: dbList.value,
          name: t('DB类型'),
          type: 'multiple' as const,
        },
        // 业务页只看当前业务，不提供所属业务筛选
        ...(options.isGlobalPage.value || options.isTodoPage.value
          ? baseSelectList
          : baseSelectList.filter((item) => item.id !== 'bk_biz_id')),
      ] as QuickSearchProps['data'],
  );

  const initTimeRange = () => {
    const startTime = route.query.start_time as string;
    const endTime = route.query.end_time as string;
    if (startTime && endTime) {
      return [dayjs(startTime).format(dateFormatStr), dayjs(endTime).format(dateFormatStr)];
    }

    return [defaultStartTime, defaultEndTime];
  };

  const initQuickSearchValue = () => {
    const initValue = baseSelectList.reduce<Record<string, string>>((result, item) => {
      const queryValue = route.query[item.id] as string;
      if (queryValue) {
        Object.assign(result, {
          [item.id]: queryValue,
        });
      }
      return result;
    }, {});

    // 未从 URL 指定过滤条件时默认只看未恢复的告警
    if (!route.query.limit && !route.query.status) {
      Object.assign(initValue, {
        status: 'ABNORMAL',
      });
    }

    Object.assign(initValue, {
      [timeRangeSearchId]: initTimeRange().join(','),
    });

    return initValue;
  };

  const quickSearchValue = ref<Record<string, string>>(initQuickSearchValue());

  watch(
    options.isTodoPage,
    () => {
      if (options.isTodoPage.value) {
        runGetUserDbaComponents();
      }
    },
    { immediate: true },
  );

  return {
    defaultEndTime,
    defaultStartTime,
    quickSearchData,
    quickSearchValue,
  };
};

// 接口的 stage / status 都是 ChoiceField 只接受单个值，表头筛选保持与快捷搜索一致的单选
export const columnFilterConfig = {
  stage: {
    component: markRaw(SingleSelect),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      list: stageList,
    },
    showConfirmAndReset: true,
  },
  status: {
    component: markRaw(SingleSelect),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      list: statusList,
    },
    showConfirmAndReset: true,
  },
} as const;
