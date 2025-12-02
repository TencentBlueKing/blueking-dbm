import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { fetchDeviceClass, fetchMountPoints, getOsTypeList } from '@services/source/dbresourceResource';
import { fetchDbTypeList, getCommonCities, getInfrasSubzonesByCity } from '@services/source/infras';
import { getCloudList, searchDeviceClass } from '@services/source/ipchooser';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { useGlobalBizs } from '@stores';

import { DeviceClass, deviceClassDisplayMap } from '@common/const';

export default (props: any) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const quickSearchValue = ref<Record<string, any>>({});

  const quickSearchData = computed(() => {
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
          id: `${item.bk_cloud_id}`,
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
          id: `${item.bk_sub_zone_id}`,
          name: item.bk_sub_zone,
        })),
        id: 'sub_zone',
        name: t('园区'),
      },
      {
        children: deviceClassList.value?.map((item) => ({
          id: `${item.id}`,
          name: item.device_type,
        })),
        id: 'device_class',
        name: t('机型'),
      },
    ];

    return serachList.filter((item) => props.params[item.id] === undefined);
  });

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

  const cityList = shallowRef<ServiceReturnType<typeof getCommonCities>['common']>([]);
  useRequest(getCommonCities, {
    onSuccess(data) {
      cityList.value = data.common.concat(data.internal).filter((item) => item.city_code !== 'default');
    },
  });

  const { data: subzoneList } = useRequest(getInfrasSubzonesByCity, {
    initialData: [],
  });

  const deviceClassList = shallowRef<ServiceReturnType<typeof fetchDeviceClass>['results']>([]);
  useRequest(fetchDeviceClass, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
      },
    ],
    onSuccess(data) {
      deviceClassList.value = data.results;
    },
  });

  const filterOption = computed(() => ({
    city: {
      component: markRaw(MultipleSelect),
      name: t('地域'),
      props: {
        list: (cityList.value || []).map((item) => ({
          label: item.city_name,
          value: item.city_code,
        })),
      },
      showConfirmAndReset: true,
    },
    device_class: {
      component: markRaw(MultipleSelect),
      name: t('机型'),
      props: {
        list: (deviceClassList.value || []).map((item) => ({
          label: item.device_type,
          value: item.id,
        })),
      },
      showConfirmAndReset: true,
    },
    subzone_ids: {
      component: markRaw(MultipleSelect),
      name: t('园区'),
      props: {
        list: (subzoneList.value || []).map((item) => ({
          label: item.bk_sub_zone,
          value: item.bk_sub_zone_id,
        })),
      },
      showConfirmAndReset: true,
    },
  }));

  return {
    filterOption,
    quickSearchData,
    quickSearchValue,
  };
};
