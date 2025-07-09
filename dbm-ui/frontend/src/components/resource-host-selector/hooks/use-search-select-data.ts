import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { fetchDeviceClass, fetchMountPoints, getOsTypeList } from '@services/source/dbresourceResource';
import { fetchDbTypeList, getInfrasCities, getInfrasSubzonesByCity } from '@services/source/infras';
import { getCloudList, searchDeviceClass } from '@services/source/ipchooser';

import { useGlobalBizs } from '@stores';

import { DeviceClass, deviceClassDisplayMap } from '@common/const';

import { getSearchSelectorParams } from '@utils';

export default (props: any) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const value = ref<ISearchValue[]>([]);
  const columnFilterValue = reactive<Record<string, string>>({});

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
        children: diskTypeList.value
          ?.filter((item) => item !== 'ALL')
          .map((item) => ({
            id: item,
            name: deviceClassDisplayMap[item as DeviceClass],
          })),
        id: 'disk_type',
        name: t('磁盘类型'),
      },
      {
        children: cityList.value?.map((item) => ({
          id: item.city_code,
          name: item.city_name,
        })),
        id: 'city',
        name: t('地域'),
      },
      {
        children: subzoneList.value?.map((item) => ({
          id: item.bk_sub_zone_id,
          name: item.bk_sub_zone,
        })),
        id: 'sub_zone',
        name: t('园区'),
      },
      {
        children: deviceClassList.value?.map((item) => ({
          id: item.id,
          name: item.device_type,
        })),
        id: 'device_class',
        name: t('机型'),
      },
    ];

    return serachList.filter((item) => props.params[item.id] === undefined);
  });

  const formatSearchValue = computed(() => getSearchSelectorParams(value.value));

  const { data: cloudList } = useRequest(getCloudList, {
    initialData: [],
  });

  const { data: diskTypeList } = useRequest(searchDeviceClass, {
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

  const cityList = shallowRef<ServiceReturnType<typeof getInfrasCities>>([]);
  useRequest(getInfrasCities, {
    onSuccess(data) {
      cityList.value = data.filter((item) => item.city_code !== 'default');
    },
  });

  const { data: subzoneList } = useRequest(getInfrasSubzonesByCity, {
    initialData: [],
  });

  const deviceClassList = shallowRef<ServiceReturnType<typeof fetchDeviceClass>['results']>([]);
  useRequest(fetchDeviceClass, {
    onSuccess(data) {
      deviceClassList.value = data.results;
    },
  });

  const filterOption = computed(() => ({
    city: {
      checked: [],
      list: (cityList.value || []).map((item) => ({
        text: item.city_name,
        value: item.city_code,
      })),
    },
    device_class: {
      checked: [],
      list: (deviceClassList.value || []).map((item) => ({
        text: item.device_type,
        value: item.id,
      })),
    },
    os_name: {
      checked: [],
      list: [],
    },
    sub_zone: {
      checked: [],
      list: (subzoneList.value || []).map((item) => ({
        text: item.bk_sub_zone,
        value: item.bk_sub_zone_id,
      })),
    },
  }));

  const handleFilter = ({ checked, field }: { checked: string[]; field: string }) => {
    Object.assign(columnFilterValue, {
      [field]: checked.length ? checked.join(',') : undefined,
    });
  };

  return {
    columnFilterValue,
    filterOption,
    formatSearchValue,
    handleFilter,
    searchSelectData,
    value,
  };
};
