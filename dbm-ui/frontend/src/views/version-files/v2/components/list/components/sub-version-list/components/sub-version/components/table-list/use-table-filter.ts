import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import DbVersionModel from '@services/model/version-file/db-version';
import { listSupportSystems } from '@services/source/package';
import { getUserList } from '@services/source/user';

import MultipleSelect from '@/components/db-table/components/MultipleSelect.vue';

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

export default (tableData: Ref<DbVersionModel[] | undefined>) => {
  const { t } = useI18n();

  const { data: supportSystems } = useRequest(listSupportSystems);

  const fullVersionSet = computed(() =>
    tableData.value
      ? tableData.value.reduce<Set<string>>((setData, item) => {
          if (!setData.has(item.full_version)) {
            setData.add(item.full_version);
          }
          return setData;
        }, new Set())
      : new Set(),
  );

  const tableFilter = computed<ITableFilter>(() => {
    return {
      description: {
        name: t('备注'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      enable: {
        component: markRaw(MultipleSelect),
        name: t('是否启用'),
        props: {
          list: [
            {
              label: t('是'),
              value: true,
            },
            {
              label: t('否'),
              value: false,
            },
          ],
        },
        showConfirmAndReset: true,
        type: 'multiple',
      },
      full_version: {
        component: markRaw(MultipleSelect),
        name: t('版本号'),
        props: {
          list: Array.from(fullVersionSet.value).map((item) => ({
            label: item,
            value: item,
          })),
        },
        showConfirmAndReset: true,
        type: 'multiple',
      },
      name: {
        name: t('版本名'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      system: {
        component: markRaw(MultipleSelect),
        name: t('操作系统限制'),
        props: {
          list: Object.keys(supportSystems.value || {}).map((item) => ({
            label: item,
            value: item,
          })),
        },
        showConfirmAndReset: true,
        type: 'multiple',
      },
      updator: {
        component: markRaw(MultipleSelect),
        name: t('更新人'),
        props: {
          remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
            const requestParams = {};
            if (params.defaultValue) {
              Object.assign(requestParams, { exact_lookups: params.defaultValue });
            }
            if (params.keyword) {
              Object.assign(requestParams, { fuzzy_lookups: params.keyword });
            }
            return getUserList(requestParams).then((res) =>
              res.results.map((item) => ({
                label: `${item.username} (${item.display_name})`,
                value: item.username,
              })),
            );
          },
          remoteSearch: true,
        },
        showConfirmAndReset: true,
      },
      version_file: {
        name: t('版本文件'),
        props: {
          autofocus: true,
        },
        showConfirmAndReset: true,
        type: 'input',
      },
    };
  });

  return tableFilter;
};
