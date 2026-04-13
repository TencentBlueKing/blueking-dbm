import dayjs from 'dayjs';
import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { queryBizInstanceAttrs } from '@services/source/dbbase';

import { clusterInstStatus, ClusterTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';
import { ipPort, ipv4 } from '@common/regex';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

const instanceAttrs = ['role', 'version', 'bk_os_name', 'bk_sub_zone'] as const;

export const useInstanceQuickSearch = (params: {
  cluster_id?: number;
  cluster_type: ClusterTypes | ClusterTypes[];
}) => {
  const { t } = useI18n();

  const isMongo =
    !Array.isArray(params.cluster_type) &&
    [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER].includes(params.cluster_type);

  const quickSearchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);

  const getBizInstanceAttrs = (attr: (typeof instanceAttrs)[number]) => {
    const instanceParams = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      instances_attrs: instanceAttrs.join(','),
    };
    if (params.cluster_id) {
      Object.assign(instanceParams, { cluster_id: params.cluster_id });
    } else {
      Object.assign(instanceParams, {
        cluster_type: Array.isArray(params.cluster_type) ? params.cluster_type.join(',') : params.cluster_type,
      });
    }
    return queryBizInstanceAttrs(instanceParams).then((data) => {
      const formatList = data[attr].map((item) => ({
        label: item.text,
        value: item.value,
      }));

      if (['bk_os_name', 'bk_sub_zone', 'version'].includes(attr)) {
        const filterList = formatList.filter((item) => item.value !== null && item.value !== '');
        if (filterList.length !== formatList.length) {
          return filterList.concat({
            label: specialOptionLabelMap[SpecialOptions.EMPTY],
            value: SpecialOptions.EMPTY,
          });
        }
        return filterList;
      }

      return formatList;
    });
  };

  const quickSearchData = _.filter(
    [
      {
        id: 'instance_address',
        name: t('实例'),
        type: 'multiple-input',
        validator: (value: string) => {
          return ipPort.test(value);
        },
      },
      {
        id: 'ip',
        name: t('主机 IP'),
        type: 'multiple-input',
        validator: (value: any) => {
          return ipv4.test(value);
        },
      },
      {
        id: isMongo ? 'cluster_name' : 'domain',
        name: t('所属集群'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !ipPort.test(value) && !ipv4.test(value);
        },
      },
      {
        id: 'id',
        name: 'ID',
        type: 'multiple-input',
        validator: (value: any) => {
          return !isNaN(Number(value)) ? true : t('ID 只支持数字');
        },
      },
      // mongodb分片集群 专属过滤项
      params.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && {
        id: 'shard',
        name: t('分片名'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !ipPort.test(value) && !ipv4.test(value);
        },
      },
      // mongodb 专属过滤项
      isMongo && {
        id: 'domain',
        name: t('域名'),
        type: 'multiple-input',
        validator: (value: string) => {
          return !ipPort.test(value) && !ipv4.test(value);
        },
      },
      {
        id: 'status',
        list: Object.entries(clusterInstStatus).map(([key, statusItem]) => ({
          label: statusItem.text,
          value: key,
        })),
        name: t('状态'),
        type: 'multiple',
      },
      {
        id: 'role',
        name: t('部署角色'),
        remoteMethod: () => getBizInstanceAttrs('role'),
        type: 'multiple',
      },
      {
        id: 'version',
        name: t('版本'),
        remoteMethod: () => getBizInstanceAttrs('version'),
        type: 'multiple',
      },
      {
        id: 'bk_sub_zone',
        name: t('园区'),
        remoteMethod: () => getBizInstanceAttrs('bk_sub_zone'),
        type: 'multiple',
      },
      {
        id: 'bk_os_name',
        name: t('操作系统'),
        remoteMethod: () => getBizInstanceAttrs('bk_os_name'),
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
    quickSearchValue,
  };
};
