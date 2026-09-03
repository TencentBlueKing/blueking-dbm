import { useI18n } from 'vue-i18n';

import { fetchResourceHostDeviceClass, getResourceOsName } from '@services/source/dbresourceResource';
import { getCommonCities, getInfrasSubzonesByCity } from '@services/source/infras';

import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

export default () => {
  const { t } = useI18n();

  return {
    city: {
      component: markRaw(MultipleSelect),
      name: t('地域'),
      props: {
        remoteMethod: () => {
          return getCommonCities().then((data) =>
            data.common.map((item) => ({
              label: item.city_name,
              value: item.city_code,
            })),
          );
        },
      },
      showConfirmAndReset: true,
    },
    device_class: {
      component: markRaw(MultipleSelect),
      name: t('机型'),
      props: {
        remoteMethod: () => {
          return fetchResourceHostDeviceClass().then((data) =>
            data.map((item) => ({
              label: item,
              value: item,
            })),
          );
        },
      },
      showConfirmAndReset: true,
    },
    os_name: {
      component: markRaw(MultipleSelect),
      name: t('操作系统名称'),
      props: {
        remoteMethod: () => {
          return getResourceOsName().then((data) =>
            data.os_names.map((item) => ({
              label: item.text,
              value: item.value,
            })),
          );
        },
      },
      showConfirmAndReset: true,
    },
    suz_zone: {
      component: markRaw(MultipleSelect),
      name: t('园区'),
      props: {
        remoteMethod: () => {
          return getInfrasSubzonesByCity().then((data) =>
            data.map((item) => ({
              label: item.bk_sub_zone,
              value: item.bk_sub_zone_id,
            })),
          );
        },
      },
      showConfirmAndReset: true,
    },
  };
};
