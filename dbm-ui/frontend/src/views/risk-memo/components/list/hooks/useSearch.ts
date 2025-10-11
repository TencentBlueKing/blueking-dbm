import type { ComponentProps } from 'vue-component-type-helpers';
import { useI18n } from 'vue-i18n';

import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import { DBTypeInfos } from '@common/const';

import DbQuickSearch from '@components/db-quick-search/Index.vue';

export type QuickSearchProps = ComponentProps<typeof DbQuickSearch>;

export default function useSearch(
  props = { isSpecial: false },
  effectBizLabels = ref<
    | {
        label: string;
        value: string;
      }[]
    | undefined
  >([]),
  exclude = ref<string[]>([]),
) {
  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const searchValue = ref<Record<string, any>>({});

  const searchSelectData = computed(() => {
    const list: QuickSearchProps['data'] = [
      {
        id: 'bk_biz_id',
        list: bizs.map((item) => ({
          label: item.name,
          value: `${item.bk_biz_id}`,
        })),
        name: t('业务'),
        type: 'single',
      },
      {
        id: 'name__icontains',
        name: props.isSpecial ? t('标题') : t('风险名称'),
      },
      {
        id: 'status',
        list: [
          {
            label: props.isSpecial ? t('生效中') : t('进行中'),
            value: 'backlog',
          },
          {
            label: props.isSpecial ? t('已失效') : t('已结项'),
            value: 'done',
          },
        ],
        name: t('状态'),
        type: 'single',
      },
      {
        id: 'db_type',
        list: Object.values(DBTypeInfos).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        name: t('DB 类型'),
        type: 'single',
      },
      {
        id: 'biz_inpact__icontains',
        list: effectBizLabels.value,
        name: t('影响范围'),
        type: 'multiple',
      },
      {
        id: 'description__icontains',
        name: props.isSpecial ? t('具体要求') : t('风险描述'),
      },
      {
        id: 'creator',
        name: t('创建人'),
        remoteMethod: requestUserList,
        remoteSearch: true,
        type: 'single',
      },
      {
        id: 'id',
        name: 'ID',
      },
      {
        id: 'follow_user',
        name: t('跟进人'),
        remoteMethod: requestUserList,
        remoteSearch: true,
        type: 'single',
      },
    ];
    return list.filter((item) => !exclude.value.includes(item.id));
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
