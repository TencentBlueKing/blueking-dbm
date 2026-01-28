import dayjs from 'dayjs';
import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import TicketModel from '@services/model/ticket/ticket';
import { getUserList } from '@services/source/user';

import { DBTypeInfos } from '@common/const';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

import { makeMap } from '@utils';

const quickSearchValue = ref<Record<string, any>>({});

export default (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();

  const quickSearchData = computed(() => {
    const serachList: Props['data'] = [
      {
        id: 'ids',
        name: t('单号'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !isNaN(Number(value)) ? true : t('单号只支持数字');
        },
      },
      {
        id: 'status',
        list: Object.keys(TicketModel.statusTextMap).reduce<Record<'label' | 'value', string>[]>((acc, key) => {
          acc.push({
            label: TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap],
            value: key,
          });
          return acc;
        }, []),
        name: t('单据状态'),
        type: 'multiple',
      },
      {
        id: 'replenish',
        name: t('补货操作 ID'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !isNaN(Number(value)) ? true : t('只支持数字');
        },
      },
      {
        id: 'db_type',
        list: Object.values(DBTypeInfos).reduce<Record<'label' | 'value', string>[]>((acc, db) => {
          acc.push({
            label: db.name,
            value: db.id,
          });
          return acc;
        }, []),
        name: t('DB 类型'),
        type: 'multiple',
      },
      {
        id: 'creator__in',
        name: t('申请人'),
        remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
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
        },
        remoteSearch: true,
        type: 'multiple',
      },
      {
        id: 'create_at',
        name: t('申请时间'),
        props: {
          shortcuts: [
            {
              text: t('近 1 小时'),
              value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
            },
            {
              text: t('近 12 小时'),
              value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
            },
            {
              text: t('今天'),
              value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
            },
            {
              text: t('近 7 天'),
              value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
            },
            {
              text: t('近 1 个月'),
              value: () => [dayjs().subtract(1, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
            },
            {
              text: t('近 3 个月'),
              value: () => [dayjs().subtract(3, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
            },
            {
              text: t('近 6 个月'),
              value: () => [dayjs().subtract(6, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
            },
          ],
        },
        type: 'datetime-range',
      },
    ] as const;

    if (!options.exclude) {
      return serachList;
    }

    const excludeMap = makeMap(options.exclude);
    return serachList.filter((item) => !excludeMap[item.id]);
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });

  return {
    quickSearchData,
    quickSearchValue,
  };
};
