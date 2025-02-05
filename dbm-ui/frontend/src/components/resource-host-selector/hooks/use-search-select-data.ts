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
        name: 'IP',
        id: 'hosts',
      },
      {
        name: t('所属业务'),
        id: 'for_biz',
        children: globalBizsStore.bizs.map((item) => ({
          id: `${item.bk_biz_id}`,
          name: item.name,
        })),
      },
      {
        name: t('所属DB类型'),
        id: 'resource_type',
        children: [{ id: 'PUBLIC', name: t('通用') }].concat(dbTypeList.value ?? []),
      },
      {
        name: t('管控区域'),
        id: 'bk_cloud_ids',
        children: cloudList.value?.map((item) => ({
          id: item.bk_cloud_id,
          name: item.bk_cloud_name,
        })),
      },
      {
        name: t('Agent 状态'),
        id: 'agent_status',
        children: [
          {
            name: t('正常'),
            id: '1',
          },
          {
            name: t('异常'),
            id: '0',
          },
        ],
      },
      {
        name: t('操作系统类型'),
        id: 'mount_point',
        children: osTypeList.value?.map((item) => ({
          id: item,
          name: item,
        })),
      },
      {
        name: t('磁盘挂载点'),
        id: 'mount_point',
        children: mountPointList.value?.map((item) => ({
          id: item,
          name: item,
        })),
      },
      {
        name: t('磁盘类型'),
        id: 'disk_type',
        children: diskTypeList.value?.map((item) => ({
          id: item,
          name: item,
        })),
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
        offset: 0,
        limit: -1,
      },
    ],
    initialData: [],
  });

  const { data: dbTypeList } = useRequest(fetchDbTypeList, {
    initialData: [],
  });

  return {
    value,
    searchSelectData,
    formatSearchValue,
  };
};
