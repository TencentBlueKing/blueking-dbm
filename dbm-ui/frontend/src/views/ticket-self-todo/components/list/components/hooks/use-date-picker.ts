import dayjs from 'dayjs';
import { computed, ref } from 'vue';

import { useUrlSearch } from '@hooks';

interface IPicker {
  value: () => [Date, Date];
}

const value = ref<[Date, Date] | [string, string]>(['', '']);

export default () => {
  const { getSearchParams } = useUrlSearch();

  const searchParams = getSearchParams();
  if (searchParams.create_at__gte && searchParams.create_at__lte) {
    value.value = [dayjs(searchParams.create_at__gte).toDate(), dayjs(searchParams.create_at__lte).toDate()];
  }

  const shortcutsRange = [
    {
      text: '今天',
      value() {
        return [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()];
      },
      onClick: (picker: IPicker) => {
        value.value = picker.value();
      },
    },
    {
      text: '近7天',
      value() {
        return [dayjs().subtract(7, 'day').toDate(), dayjs().toDate()];
      },
      onClick: (picker: IPicker) => {
        value.value = picker.value();
      },
    },
    {
      text: '近15天',
      value() {
        return [dayjs().subtract(15, 'day').toDate(), dayjs().toDate()];
      },
      onClick: (picker: IPicker) => {
        value.value = picker.value();
      },
    },
    {
      text: '近30天',
      value() {
        return [dayjs().subtract(30, 'day').toDate(), dayjs().toDate()];
      },
      onClick: (picker: IPicker) => {
        value.value = picker.value();
      },
    },
  ];

  const formatValue = computed(() => {
    if (value.value[0] && value.value[1]) {
      return {
        create_at__gte: dayjs(value.value[0]).format('YYYY-MM-DD HH:mm:ss'),
        create_at__lte: dayjs(value.value[1]).format('YYYY-MM-DD HH:mm:ss'),
      };
    }
    return {};
  });

  return {
    value,
    formatValue,
    shortcutsRange,
  };
};
