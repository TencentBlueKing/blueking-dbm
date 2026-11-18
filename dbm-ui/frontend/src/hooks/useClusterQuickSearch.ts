import dayjs from 'dayjs';
import _ from 'lodash';
import { computed, markRaw, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getClusterStateSchema } from '@services/source/clusterState';
import { queryBizClusterAttrs } from '@services/source/dbbase';
import { listTag } from '@services/source/tag';
import { getUserList } from '@services/source/user';

import { clusterTypeInfos, ClusterTypes } from '@common/const';
import { domainPort, domainRegex, ipPort, ipv4 } from '@common/regex';

import ClusterStateSearchPanel from '@components/cluster-state-search-panel/Index.vue';
import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

import {
  clusterStateSupportedTypes,
  formatClusterStateFilterText,
  getClusterStateFilterCascaderList,
  getClusterStateFilterFields,
} from './useClusterStateSchema';

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

  const isClusterStateSupported = !Array.isArray(cluster_type) && clusterStateSupportedTypes.includes(cluster_type);
  // 运行概况字段 key 与名称的映射，用于标签回显「字段名 ： 取值」
  const clusterStateFieldNameMap = ref<Record<string, string>>({});

  const getClusterStateCascaderList = () =>
    getClusterStateSchema({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: cluster_type as ClusterTypes,
    }).then((schema) => {
      const fields = getClusterStateFilterFields(schema);
      clusterStateFieldNameMap.value = fields.reduce<Record<string, string>>(
        (result, field) => Object.assign(result, { [field.key]: field.name }),
        {},
      );
      return getClusterStateFilterCascaderList(fields);
    });

  if (isClusterStateSupported) {
    // 预取字段名，标签回显时可直接取到；接口带缓存，面板打开时不会重复请求
    getClusterStateCascaderList().catch(_.noop);
  }

  const getBizClusterAttrs = (attr: (typeof clusterAttrs)[number]) => {
    return queryBizClusterAttrs({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_attrs: clusterAttrs.join(','),
      cluster_type: cluster_type,
    }).then((data) => {
      return data[attr].map((item) => ({
        label: attr === 'bk_cloud_id' ? `${item.text}[${item.value}]` : item.text,
        value: item.value,
      }));
    });
  };

  const quickSearchData = _.filter(
    [
      {
        description: t('单个值支持模糊搜索'),
        id: 'domain',
        name: t('访问入口（域名 / CLB / 北极星）'),
        type: 'multiple-input',
        validator: (value: string) => {
          // 排除 IP:Port（归实例），CLB 等入口可能是纯 IPv4，放行
          return !ipPort.test(value);
        },
      },

      {
        id: 'instance',
        name: t('实例（IP / IP:Port）'),
        type: 'multiple-input',
        validator: (value: string) => {
          return ipPort.test(value) || ipv4.test(value);
        },
      },
      {
        id: 'cluster_ids',
        name: 'ID',
        type: 'multiple-input',
        validator: (value) => {
          return !isNaN(Number(value)) ? true : t('ID 只支持数字');
        },
      },
      // redis 专属过滤项(仅在 cluster_type 为 redis 集群时是数组时)
      Array.isArray(cluster_type) && {
        id: 'redis_cluster_type',
        list: cluster_type.map((redisClusterType) => ({
          label: clusterTypeInfos[redisClusterType].name,
          value: redisClusterType,
        })),
        name: t('架构类型'),
        type: 'multiple',
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
                value: `tag_ids#${item.id}`,
              });
            });

            return Object.keys(keyValueMap).map((tagKey) => ({
              children: keyValueMap[tagKey],
              label: tagKey,
              value: `tag_keys#${tagKey}`,
            }));
          }),
        type: 'multiple-cascader',
      },
      {
        description: t('单个值支持模糊搜索'),
        id: 'name',
        name: t('集群标识（集群名称 / 别名）'),
        type: 'input',
        validator: (value) => {
          // 排除IP和IP:Port和域名和域名:Port
          return !ipPort.test(value) && !ipv4.test(value) && !domainRegex.test(value) && !domainPort.test(value);
        },
      },
      !Array.isArray(cluster_type) &&
        [
          ClusterTypes.RIAK,
          ClusterTypes.SQLSERVER_HA,
          ClusterTypes.SQLSERVER_SINGLE,
          ClusterTypes.TENDBCLUSTER,
          ClusterTypes.TENDBHA,
          ClusterTypes.TENDBSINGLE,
        ].includes(cluster_type) && {
          id: 'db_module_id',
          name: t('模块'),
          remoteMethod: () => getBizClusterAttrs('db_module_id'),
          type: 'multiple',
        },
      // 接入运行概况的集群类型去掉原「状态」条件，状态筛选统一走「运行概况」（产品 2026-11-17 需求备注）
      !isClusterStateSupported && {
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
      isClusterStateSupported && {
        component: markRaw(ClusterStateSearchPanel),
        formatValuesText: (values: { label: string; value: string | number }[]) =>
          formatClusterStateFilterText(values, clusterStateFieldNameMap.value),
        id: 'cluster_state',
        name: t('运行概况'),
        props: {
          clusterType: cluster_type,
        },
        // 面板自行取字段；这里的候选只用于 URL 回显时把编码值还原成文案
        remoteMethod: getClusterStateCascaderList,
        type: 'multiple-cascader',
      },
      {
        id: 'major_version',
        name: t('版本'),
        remoteMethod: () => getBizClusterAttrs('major_version'),
        type: 'multiple',
      },
      (Array.isArray(cluster_type) || !cluster_type.includes('k8s')) && {
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
      (Array.isArray(cluster_type) || !cluster_type.includes('k8s')) && {
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
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  return {
    isSearching,
    quickSearchData,
    searchValue,
  };
};
