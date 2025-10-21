import dayjs from 'dayjs';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { queryBizClusterAttrs } from '@services/source/dbbase';
import { listTag } from '@services/source/tag';
import { getUserList } from '@services/source/user';

import { ClusterTypes } from '@common/const';
import { domainPort, domainRegex, ipPort, ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

const clusterAttrs = [
  'bk_cloud_id',
  'db_module_id',
  'major_version',
  'region',
  'time_zone',
  'disaster_tolerance_level',
] as const;

export const useClusterQuickSearch = (cluster_type: ClusterTypes | ClusterTypes[]) => {
  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(searchValue.value).length > 0);

  const getBizClusterAttrs = (attr: (typeof clusterAttrs)[number]) => {
    return queryBizClusterAttrs({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_attrs: clusterAttrs.join(','),
      cluster_type: Array.isArray(cluster_type) ? cluster_type.join(',') : cluster_type,
    }).then((data) => {
      return data[attr].map((item) => ({
        label: item.text,
        value: item.value,
      }));
    });
  };

  const quickSearchData: QuickSearchProps['data'] = [
    {
      description: t('支持模糊搜索'),
      id: 'domain',
      name: t('访问入口'),
      type: 'multiple-input',
      validator: (value) => {
        return !ipPort.test(value) && !ipv4.test(value);
      },
    },

    {
      description: t('支持模糊搜索'),
      id: 'instance',
      name: t('IP 或 IP:Port'),
      type: 'multiple-input',
      validator: (value) => {
        return ipPort.test(value) || ipv4.test(value);
      },
    },
    {
      id: 'tag',
      name: t('标签'),
      props: {
        checkStrictly: true,
        showAllLevels: true,
      },
      remoteMethod: () =>
        listTag(
          {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            limit: -1,
            offset: 0,
            type: 'cluster',
          },
          {
            cache: true,
          },
        ).then((data) => {
          const keyValueMap: Record<string, { label: string; value: string }[]> = {};
          data.results.forEach((item) => {
            if (!keyValueMap[item.key]) {
              keyValueMap[item.key] = [];
            }
            keyValueMap[item.key].push({
              label: item.value,
              value: `tag_ids=${item.id}`,
            });
          });

          return Object.keys(keyValueMap).map((tagKey) => ({
            children: keyValueMap[tagKey],
            label: tagKey,
            value: `tag_keys=${tagKey}`,
          }));
        }),
      type: 'multiple-cascader',
    },
    {
      description: t('支持模糊搜索'),
      id: 'name',
      name: t('集群名称'),
      type: 'multiple-input',
      validator: (value) => {
        // 排除IP和IP:Port和域名和域名:Port
        return !ipPort.test(value) && !ipv4.test(value) && !domainRegex.test(value) && !domainPort.test(value);
      },
    },
    {
      id: 'status',
      list: [
        {
          label: t('正常'),
          value: 'normal',
        },
        {
          label: t('异常'),
          value: 'abnormal',
        },
      ],
      name: t('状态'),
      type: 'multiple',
    },
    {
      id: 'db_module_id',
      name: t('模块'),
      remoteMethod: () => getBizClusterAttrs('db_module_id'),
      type: 'multiple',
    },
    {
      id: 'major_version',
      name: t('版本'),
      remoteMethod: () => getBizClusterAttrs('major_version'),
      type: 'multiple',
    },
    {
      id: 'disaster_tolerance_level',
      name: t('容灾要求'),
      remoteMethod: () => getBizClusterAttrs('disaster_tolerance_level'),
      type: 'multiple',
    },
    {
      id: 'region',
      name: t('地域'),
      remoteMethod: () => getBizClusterAttrs('region'),
      type: 'multiple',
    },
    {
      id: 'bk_cloud_id',
      name: t('管控区域'),
      remoteMethod: () => getBizClusterAttrs('bk_cloud_id'),
      type: 'multiple',
    },
    {
      id: 'time_zone',
      name: t('时区'),
      remoteMethod: () => getBizClusterAttrs('time_zone'),
      type: 'multiple',
    },
    {
      id: 'creator',
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
      id: 'create_at',
      name: t('部署时间'),
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
  ];

  return {
    isSearching,
    quickSearchData,
    searchValue,
  };
};
