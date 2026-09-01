import dayjs from 'dayjs';
import { markRaw, ref, shallowRef } from 'vue';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import SingleSelect from '@components/db-table/components/SingleSelect.vue';

import { t } from '@/locales';

// 屏蔽类型选项，快捷搜索与表头筛选共用
const shieldCategoryList = [
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
];

// 屏蔽时间快捷选项，快捷搜索与表头筛选共用
const shieldTimeShortcuts: { text: string; value: () => [Date, Date] }[] = [
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

export const useQuickSearch = () => {
  const quickSearchValue = ref<Record<string, string>>({});

  const quickSearchData = [
    {
      id: 'category',
      list: shieldCategoryList,
      name: t('屏蔽类型'),
      type: 'single',
    },
    {
      id: 'time_range',
      name: t('屏蔽时间'),
      props: {
        shortcuts: shieldTimeShortcuts,
      },
      type: 'datetime-range',
    },
  ] as QuickSearchProps['data'];

  return {
    quickSearchData,
    quickSearchValue,
  };
};

export const useColumnFilter = () => {
  const data = shallowRef<{
    [K in keyof typeof baseFilter]: {
      component?: any;
      popupProps: {
        attach: 'body';
        placement: 'bottom';
      };
      props: Record<string, any>;
      showConfirmAndReset?: boolean;
    };
  }>();

  // 接口的 category 只接受单个值，表头筛选保持与快捷搜索一致的单选
  const baseFilter = {
    category: {
      component: markRaw(SingleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: shieldCategoryList,
      },
      showConfirmAndReset: true,
    },
    time_range: {
      component: markRaw(DatetimeRange),
      name: t('屏蔽时间'),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        shortcuts: shieldTimeShortcuts,
      },
      showConfirmAndReset: true,
    },
  } as const;

  data.value = baseFilter;

  return {
    data,
  };
};
