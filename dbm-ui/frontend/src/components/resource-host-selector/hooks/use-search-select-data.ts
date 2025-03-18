import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { fetchDiskTypes, fetchMountPoints, getOsTypeList } from '@services/source/dbresourceResource';
import { fetchDbTypeList } from '@services/source/infras';
import { getCloudList } from '@services/source/ipchooser';

import { useGlobalBizs } from '@stores';

import type { SearchValue } from '@components/vue2/search-select/index.vue';

import { getSearchSelectorParams } from '@utils';

export default (props: any) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const value = ref<SearchValue[]>([]);

  const searchSelectData = computed(() => {
    const serachList = [
      {
        id: 'hosts',
        name: 'IP',
      },
      {
        children: globalBizsStore.bizs.map((item) => ({
          id: `${item.bk_biz_id}`,
          name: item.name,
        })),
        id: 'for_biz',
        name: t('所属业务'),
      },
      {
        children: [{ id: 'PUBLIC', name: t('通用') }].concat(dbTypeList.value ?? []),
        id: 'resource_type',
        name: t('所属DB类型'),
      },
      {
        children: cloudList.value?.map((item) => ({
          id: item.bk_cloud_id,
          name: item.bk_cloud_name,
        })),
        id: 'bk_cloud_ids',
        name: t('管控区域'),
      },
      {
        children: [
          {
            id: '1',
            name: t('正常'),
          },
          {
            id: '0',
            name: t('异常'),
          },
        ],
        id: 'agent_status',
        name: t('Agent 状态'),
      },
      {
        children: osTypeList.value?.map((item) => ({
          id: item,
          name: item,
        })),
        id: 'mount_point',
        name: t('操作系统类型'),
      },
      {
        children: mountPointList.value?.map((item) => ({
          id: item,
          name: item,
        })),
        id: 'mount_point',
        name: t('磁盘挂载点'),
      },
      {
        children: diskTypeList.value?.map((item) => ({
          id: item,
          name: item,
        })),
        id: 'disk_type',
        name: t('磁盘类型'),
      },
    ];

    return serachList.filter((item) => props.params[item.id] === undefined);
  });

  const formatSearchValue = computed(() => getSearchSelectorParams(value.value));

  const { data: cloudList } = useRequest(getCloudList, {
    initialData: [],
  });

  const { data: diskTypeList } = useRequest(fetchDiskTypes, {
    initialData: [],
  });

  const { data: mountPointList } = useRequest(fetchMountPoints, {
    initialData: [],
  });

  const { data: osTypeList } = useRequest(getOsTypeList, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
      },
    ],
    initialData: [],
  });

  const { data: dbTypeList } = useRequest(fetchDbTypeList, {
    initialData: [],
  });

  return {
    formatSearchValue,
    searchSelectData,
    value,
  };
};
