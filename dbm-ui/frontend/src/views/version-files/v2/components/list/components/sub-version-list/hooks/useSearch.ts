import type { ComponentProps } from 'vue-component-type-helpers';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import DbQuickSearch from '@components/db-quick-search/Index.vue';

export type QuickSearchProps = ComponentProps<typeof DbQuickSearch>;

export default function useSearch() {
  const { t } = useI18n();

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
        id: 'enable',
        list: [
          {
            label: t('是'),
            value: true as any,
          },
          {
            label: t('否'),
            value: false as any,
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
