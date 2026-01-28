import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { DBTypeInfos } from '@common/const';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

import { makeMap } from '@utils';

const quickSearchValue = ref<Record<string, any>>({});

export default (options = {} as { exclude: string[] }) => {
  const { t } = useI18n();

  const quickSearchData = computed(() => {
    const serachList: Props['data'] = [
      {
        id: 'id',
        name: 'ID',
        type: 'input',
        validator: (value: string) => {
          return !isNaN(Number(value)) ? true : t('ID 只支持数字');
        },
      },
      {
        id: 'db_type',
        list: Object.values(DBTypeInfos).reduce<Record<'label' | 'value', string>[]>((acc, db) => {
          acc.push({
            label: db.name,
            value: db.id,
          });
          return acc;
        }, []),
        name: t('DB 类型'),
        type: 'multiple',
      },
      {
        id: 'creator',
        name: t('申请人'),
        remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
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
        },
        remoteSearch: true,
        type: 'multiple',
      },
    ] as const;

    if (!options.exclude) {
      return serachList;
    }

    const excludeMap = makeMap(options.exclude);
    return serachList.filter((item) => !excludeMap[item.id]);
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });

  return {
    quickSearchData,
    quickSearchValue,
  };
};
