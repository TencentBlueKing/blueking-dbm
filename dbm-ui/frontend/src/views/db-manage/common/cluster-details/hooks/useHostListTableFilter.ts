import { useI18n } from 'vue-i18n';

import { queryBizMachineAttrs } from '@services/source/dbbase';

import { ClusterTypes, getCloudZoneName, specialOptionLabelMap, SpecialOptions } from '@common/const';

import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

const machineAttrs = [
  'bk_city_id',
  'bk_sub_zone',
  'bk_cloud_region',
  'bk_cloud_zone',
  'bk_os_name',
  'spec_id',
  'instance_role',
  'bk_svr_device_cls_name',
] as const;

export const useHostListTableFilter = (clusterType: ClusterTypes, clusterId: number) => {
  const { t } = useI18n();

  const getBizMachineAttrs = (attr: (typeof machineAttrs)[number]) => {
    return queryBizMachineAttrs({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: clusterId,
      cluster_type: clusterType,
      machine_attrs: machineAttrs.join(','),
    }).then((data) => {
      const getLabel = (item: { text: string; value: string }) => {
        if (attr === 'spec_id') {
          return `${item.text} [${item.value}]`;
        }
        if (attr === 'bk_cloud_zone') {
          return getCloudZoneName(item.value) || item.text;
        }

        return item.text;
      };

      const formatList = data[attr].map((item) => ({
        label: getLabel(item),
        value: item.value,
      }));

      if (
        [
          'bk_city_id',
          'bk_cloud_region',
          'bk_cloud_zone',
          'bk_os_name',
          'bk_sub_zone',
          'bk_svr_device_cls_name',
        ].includes(attr)
      ) {
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

  return {
    bk_city_id: {
      component: markRaw(MultipleSelect),
      name: t('城市'),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_city_id'),
      },
      showConfirmAndReset: true,
    },
    bk_cloud_region: {
      component: markRaw(MultipleSelect),
      name: t('地域'),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_cloud_region'),
      },
      showConfirmAndReset: true,
    },
    bk_cloud_zone: {
      component: markRaw(MultipleSelect),
      name: t('可用区'),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_cloud_zone'),
      },
      showConfirmAndReset: true,
    },
    bk_os_name: {
      component: markRaw(MultipleSelect),
      name: t('操作系统'),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_os_name'),
      },
      showConfirmAndReset: true,
    },
    bk_sub_zone: {
      component: markRaw(MultipleSelect),
      name: t('园区'),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_sub_zone'),
      },
      showConfirmAndReset: true,
    },
    bk_svr_device_cls_name: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_svr_device_cls_name'),
      },
      showConfirmAndReset: true,
    },
    instance_role: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('instance_role'),
      },
      showConfirmAndReset: true,
    },
    ip: {
      component: markRaw(MultipleInput),
      name: 'IP',
      props: {
        autofocus: true,
      },
      showConfirmAndReset: true,
    },
    spec_id: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('spec_id'),
      },
      showConfirmAndReset: true,
    },
  };
};
