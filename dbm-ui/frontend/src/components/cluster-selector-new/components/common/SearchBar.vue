<template>
  <DbSearchSelect
    v-model="searchSelectValue"
    class="mb-16"
    :data="searchSelectData"
    :placeholder="placeholder ? placeholder : t('集群_模块')"
    unique-select />
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';

  import { useGlobalBizs } from '@stores';

  export type SearchSelectList = {
    id: string;
    name: string;
    children?: {
      id: string | number;
      name: string;
    }[];
  }[];

  interface Props {
    clusterType: string;
    searchSelectList?: SearchSelectList;
    placeholder?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    searchSelectList: undefined,
    placeholder: '',
  });

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const dbModuleList = shallowRef<{ id: number; name: string }[]>([]);

  const searchSelectData = computed(() =>
    props.searchSelectList
      ? props.searchSelectList
      : [
          {
            name: t('集群'),
            id: 'domain',
          },
          {
            name: t('模块'),
            id: 'db_module_id',
            children: dbModuleList.value,
          },
        ],
  );

  const { run: rungGetModules } = useRequest(getModules, {
    manual: true,
    onSuccess(res) {
      dbModuleList.value = res.map((item) => ({
        id: item.db_module_id,
        name: item.name,
      }));
    },
  });

  watch(
    () => props.clusterType,
    (type) => {
      // 取默认才查询
      if (!props.searchSelectList && type) {
        rungGetModules({
          bk_biz_id: currentBizId,
          cluster_type: type,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
