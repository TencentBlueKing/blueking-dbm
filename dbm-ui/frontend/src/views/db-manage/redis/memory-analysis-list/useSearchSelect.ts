import dayjs from 'dayjs';
import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import RedisKeystatAnalysisModel from '@services/model/redis/redis-keystat-analysis';
import { getUserList } from '@services/source/user';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

import { makeMap } from '@utils';

export default (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();
  const quickSearchValue = ref<Record<string, any>>({
    create_at: `${dayjs().subtract(15, 'day').startOf('day').format('YYYY-MM-DD HH:mm:ss')},${dayjs().endOf('day').format('YYYY-MM-DD HH:mm:ss')}`,
  });

  const quickSearchData = computed(() => {
    const serachList: Props['data'] = [
      {
        id: 'immute_domain',
        name: t('集群'),
        type: 'multiple-input',
      },
      {
        id: 'instance_addresses',
        name: t('实例'),
        type: 'multiple-input',
      },
      {
        id: 'status',
        list: Object.keys(RedisKeystatAnalysisModel.STATUS_TEXT_MAP).reduce<Record<'label' | 'value', string>[]>(
          (acc, key) => {
            acc.push({
              label:
                RedisKeystatAnalysisModel.STATUS_TEXT_MAP[
                  key as keyof typeof RedisKeystatAnalysisModel.STATUS_TEXT_MAP
                ],
              value: key,
            });
            return acc;
          },
          [],
        ),
        name: t('任务状态'),
        type: 'multiple',
      },
      {
        id: 'operator',
        name: t('创建人'),
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
        id: 'ticket_id',
        name: t('关联单据'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !isNaN(Number(value)) ? true : t('单号只支持数字');
        },
      },
      {
        id: 'create_at',
        name: t('提单时间'),
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
