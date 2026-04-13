import _ from 'lodash';
import { watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { queryBizMachineAttrs } from '@services/source/dbbase';

import { useUrlSearch } from '@hooks';

import { ClusterTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';
import { batchSplitRegex, ipv4 } from '@common/regex';

import { URL_HOST_MEMO_KEY } from '../constants';

const machineAttrs = [
  'bk_city_id',
  'bk_sub_zone',
  'bk_os_name',
  'spec_id',
  'instance_role',
  'bk_svr_device_cls_name',
] as const;

const quickSearchValue = ref<Record<string, any>>({});

export const useHostSearchSelect = (
  clusterType: ClusterTypes,
  options: {
    clusterId: number;
    serviceHandler: () => void;
  },
) => {
  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { getSearchParams } = useUrlSearch();

  const getBizMachineAttrs = (attr: (typeof machineAttrs)[number]) => {
    return queryBizMachineAttrs({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: options.clusterId,
      cluster_type: clusterType,
      machine_attrs: machineAttrs.join(','),
    }).then((data) => {
      const formatList = data[attr].map((item) => ({
        label: attr === 'spec_id' ? `${item.text} [${item.value}]` : item.text,
        value: item.value,
      }));

      if (['bk_city_id', 'bk_os_name', 'bk_sub_zone', 'bk_svr_device_cls_name'].includes(attr)) {
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

  const quickSearchData = [
    {
      id: 'ip',
      name: 'IP',
      type: 'multiple-input' as const,
      validator: (value: string) => {
        if (value.split(batchSplitRegex).some((item) => !ipv4.test(item))) {
          return t('格式错误');
        }
        return true;
      },
    },
    {
      id: 'instance_role',
      name: t('部署角色'),
      remoteMethod: () => getBizMachineAttrs('instance_role'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_city_id',
      name: t('地域'),
      remoteMethod: () => getBizMachineAttrs('bk_city_id'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_sub_zone',
      name: t('园区'),
      remoteMethod: () => getBizMachineAttrs('bk_sub_zone'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_os_name',
      name: t('操作系统'),
      remoteMethod: () => getBizMachineAttrs('bk_os_name'),
      type: 'multiple' as const,
    },
    {
      id: 'spec_id',
      name: t('绑定规格'),
      remoteMethod: () => getBizMachineAttrs('spec_id'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_svr_device_cls_name',
      name: t('机型'),
      remoteMethod: () => getBizMachineAttrs('bk_svr_device_cls_name'),
      type: 'multiple' as const,
    },
  ];

  quickSearchValue.value = JSON.parse(decodeURIComponent(String(route.query[URL_HOST_MEMO_KEY] || '{}')));

  watch(
    quickSearchValue,
    _.debounce(() => {
      options.serviceHandler();
      router.replace({
        query: {
          ...getSearchParams(),
          [URL_HOST_MEMO_KEY]: encodeURIComponent(JSON.stringify(quickSearchValue.value)),
        },
      });
    }, 200),
  );

  return {
    quickSearchData,
    quickSearchValue,
  };
};
