import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { getResourceSpecList } from '@services/source/dbresourceSpec';

import { DBTypeInfos, DBTypes } from '@common/const';

import MultCascader from '@components/db-table/components/MultCascader.vue';
import SingleSelect from '@components/db-table/components/SingleSelect.vue';

type ITableFilter = Record<
  string,
  {
    component?: any;
    confirmEvents?: string[];
    list?:
      | {
          label: string;
          value: string;
        }[]
      | {
          children: {
            label: string;
            value: string;
          }[];
          label: string;
          value: string;
        }[];
    name: string;
    props?: Record<string, any>;
    type?: 'multiple' | 'single' | 'input';
  }
>;

export const useTableFilter = (
  dbType: DBTypes,
  options = {} as {
    roleList: Ref<
      {
        label: string;
        value: string;
      }[]
    >;
  },
) => {
  const { t } = useI18n();

  const specList = shallowRef<
    {
      children: {
        label: string;
        value: string;
      }[];
      label: string;
      value: string;
    }[]
  >([]);

  const tableFilter = computed<ITableFilter>(() => {
    return {
      bk_os_name: {
        name: t('操作系统'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      bk_sub_zone: {
        name: t('园区'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      bk_svr_device_cls_name: {
        name: t('机型'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      instance_role: {
        component: markRaw(SingleSelect),
        name: t('部署角色'),
        props: {
          list: options.roleList.value,
        },
        showConfirmAndReset: true,
      },
      ip: {
        name: 'IP',
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      region: {
        name: t('地域'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      spec_ids: {
        component: markRaw(MultCascader),
        name: t('绑定规格'),
        props: {
          list: specList.value,
        },
        showConfirmAndReset: true,
      },
    };
  });

  useRequest(getResourceSpecList, {
    defaultParams: [{ limit: -1, spec_cluster_type: dbType }],
    onSuccess(specResult) {
      const specMap = specResult.results.reduce<
        Record<
          string,
          {
            label: string;
            value: number;
          }[]
        >
      >((prev, specItem) => {
        const optionItem = {
          label: specItem.spec_name,
          value: specItem.spec_id,
        };
        if (prev[specItem.spec_machine_type]) {
          return Object.assign(prev, {
            [specItem.spec_machine_type]: prev[specItem.spec_machine_type]!.concat(optionItem),
          });
        }
        return Object.assign(prev, { [specItem.spec_machine_type]: [optionItem] });
      }, {});

      const { machineList } = DBTypeInfos[dbType];
      specList.value = machineList.map((machineItem) =>
        Object.assign(machineItem, { children: specMap[machineItem.value] }),
      );
    },
  });

  return tableFilter;
};
