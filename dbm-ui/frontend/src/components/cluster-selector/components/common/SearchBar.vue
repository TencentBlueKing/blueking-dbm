<template>
  <DbSearchSelect
    v-model="searchSelectValue"
    class="mb-16"
    :data="searchSelectData"
    :placeholder="placeholder ? placeholder : t('请输入或选择条件搜索')"
    unique-select />
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  import { ClusterTypes } from '@common/const';

  export type SearchSelectList = {
    id: string,
    name: string,
    children?: {
      id: string | number,
      name: string,
    }[]
  }[]

  interface Props {
    clusterType: ClusterTypes,
    searchAttrs: SearchAttrs,
    searchSelectList?: SearchSelectList,
    placeholder?: string
  }

  const props = withDefaults(defineProps<Props>(), {
    searchSelectList: undefined,
    placeholder: '',
  });

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();

  const showDbModuleSelect = computed(() => [
    ClusterTypes.TENDBHA,
    ClusterTypes.TENDBSINGLE,
  ].includes(props.clusterType));

  const searchSelectData = computed(() => {
    const baseSelectList = [
      {
        name: t('访问入口'),
        id: 'domain',
        multiple: true,
      },
      {
        name: t('状态'),
        id: 'status',
        multiple: true,
        children: [
          {
            id: 'normal',
            name: t('正常'),
          },
          {
            id: 'abnormal',
            name: t('异常'),
          },
        ],
      },
      {
        name: t('集群名称'),
        id: 'name',
        multiple: true,
      },
      {
        name: t('管控区域'),
        id: 'bk_cloud_id',
        multiple: true,
        children: props.searchAttrs.bk_cloud_id,
      },
    ];
    if (showDbModuleSelect.value) {
      const dbModuleSelect = {
        name: t('所属模块'),
        id: 'db_module_id',
        multiple: true,
        children: props.searchAttrs.db_module_id,
      };
      baseSelectList.splice(3, 0, dbModuleSelect);
    }
    return (props.searchSelectList ? props.searchSelectList : baseSelectList);
  });
</script>
