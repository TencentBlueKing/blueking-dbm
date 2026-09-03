import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { fetchMountPoints, fetchResourceHostDeviceClass, getOsTypeList } from '@services/source/dbresourceResource';
import { getCommonCities, getInfrasSubzonesByCity } from '@services/source/infras';
import { getCloudList, searchDeviceClass } from '@services/source/ipchooser';

import { useGlobalBizs } from '@stores';

import {
  DeviceClass,
  deviceClassDisplayMap,
  readResourceDbTypes,
  specialOptionLabelMap,
  SpecialOptions,
} from '@common/const';

import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

export default (props: any) => {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const quickSearchValue = ref<Record<string, any>>({});

  const quickSearchData = computed(() => {
    const serachList = [
      {
        id: 'hosts',
        name: 'IP',
        type: 'multiple-input',
      },
      {
        id: 'for_biz',
        list: globalBizsStore.bizs.map((item) => ({
          label: item.name,
          value: `${item.bk_biz_id}`,
        })),
        name: t('所属业务'),
        type: 'single',
      },
      {
        id: 'resource_type',
        list: readResourceDbTypes.concat({
          label: specialOptionLabelMap[SpecialOptions.PUBLIC],
          value: SpecialOptions.PUBLIC,
        }),
        name: t('所属DB类型'),
        type: 'single',
      },
      {
        id: 'bk_cloud_ids',
        list: cloudList.value?.map((item) => ({
          label: item.bk_cloud_name,
          value: `${item.bk_cloud_id}`,
        })),
        name: t('管控区域'),
        type: 'multiple',
      },
      {
        id: 'agent_status',
        list: [
          {
            label: t('正常'),
            value: '1',
          },
          {
            label: t('异常'),
            value: '0',
          },
        ],
        name: t('Agent 状态'),
        type: 'single',
      },
      {
        id: 'mount_point',
        list: osTypeList.value?.map((item) => ({
          label: item,
          value: item,
        })),
        name: t('操作系统类型'),
        type: 'single',
      },
      {
        id: 'mount_point',
        list: mountPointList.value?.map((item) => ({
          label: item,
          value: item,
        })),
        name: t('数据盘挂载点'),
        type: 'single',
      },
      {
        id: 'disk_type',
        list: diskTypeList.value
          ?.filter((item) => item !== 'ALL')
          .map((item) => ({
            label: deviceClassDisplayMap[item as DeviceClass],
            value: item,
          })),
        name: t('数据盘类型'),
        type: 'single',
      },
      {
        id: 'city',
        list: cityList.value?.map((item) => ({
          label: item.city_name,
          value: item.city_code,
        })),
        name: t('地域'),
        type: 'multiple',
      },
      {
        id: 'sub_zone',
        list: subzoneList.value?.map((item) => ({
          label: item.bk_sub_zone,
          value: `${item.bk_sub_zone_id}`,
        })),
        name: t('园区'),
        type: 'multiple',
      },
      {
        id: 'device_class',
        list: deviceClassList.value?.map((item) => ({
          label: item,
          value: item,
        })),
        name: t('机型'),
        type: 'multiple',
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

  const cityList = shallowRef<ServiceReturnType<typeof getCommonCities>['common']>([]);
  useRequest(getCommonCities, {
    onSuccess(data) {
      cityList.value = data.common.concat(data.internal).filter((item) => item.city_code !== 'default');
    },
  });

  const { data: subzoneList } = useRequest(getInfrasSubzonesByCity, {
    initialData: [],
  });

  const { data: deviceClassList } = useRequest(fetchResourceHostDeviceClass, {
    initialData: [],
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
          label: item,
          value: item,
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
