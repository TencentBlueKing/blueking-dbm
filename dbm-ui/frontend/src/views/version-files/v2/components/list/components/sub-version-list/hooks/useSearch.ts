import type { ComponentProps } from 'vue-component-type-helpers';
import { useI18n } from 'vue-i18n';
import { useRequest } from 'vue-request';

import { listSupportSystems } from '@services/source/package';
import { getUserList } from '@services/source/user';

import DbQuickSearch from '@components/db-quick-search/Index.vue';

export type QuickSearchProps = ComponentProps<typeof DbQuickSearch>;

export default function useSearch() {
  const { t } = useI18n();
  const { data: supportSystems } = useRequest(listSupportSystems);

  const searchValue = ref<Record<string, any>>({});

  const searchSelectData = computed(() => {
    const list: QuickSearchProps['data'] = [
      {
        id: 'full_version',
        name: t('版本号'),
      },
      {
        id: 'name',
        name: t('版本名'),
      },
      {
        id: 'system',
        list: Object.keys(supportSystems.value || {}).map((item) => ({
          label: item,
          value: item,
        })),
        name: t('操作系统限制'),
        type: 'multiple',
      },
      {
        id: 'version_file',
        name: t('版本文件'),
      },
      {
        id: 'enable',
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
        name: t('是否启用'),
        type: 'multiple',
      },
      {
        id: 'description',
        name: t('描述'),
      },
      {
        id: 'updater',
        name: t('更新人'),
        remoteMethod: requestUserList,
        remoteSearch: true,
        type: 'multiple',
      },
    ];
    return list;
  });

  const requestUserList = (params: { defaultValue?: string; keyword?: string }) => {
    const requestParams = {};
    if (params.defaultValue) {
      Object.assign(requestParams, { exact_lookups: params.defaultValue });
    }
    if (params.keyword) {
      Object.assign(requestParams, { fuzzy_lookups: params.keyword });
    }

    return getUserList(requestParams).then((data) =>
      data.results.map((item) => ({
        label: `${item.username} (${item.display_name})`,
        value: item.username,
      })),
    );
  };

  return {
    searchSelectData,
    searchValue,
  };
}
