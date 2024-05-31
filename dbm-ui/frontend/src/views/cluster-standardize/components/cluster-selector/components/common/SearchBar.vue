<template>
  <DbSearchSelect
    class="mb-16"
    :data="searchSelectData"
    :model-value="searchSelectValue"
    :placeholder="t('请输入或选择条件搜索')"
    unique-select
    :validate-values="validateSearchValues"
    @change="handleSearchChange" />
</template>
<script setup lang="ts">
  import type { ISearchValue, ValidateValuesFunc } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  export type SearchSelectList = {
    id: string;
    name: string;
    children?: {
      id: string | number;
      name: string;
    }[];
  }[];

  interface Props {
    searchAttrs: SearchAttrs;
    validateSearchValues: ValidateValuesFunc;
    searchSelectList?: SearchSelectList;
  }

  interface Emits {
    (e: 'searchValueChange', value: ISearchValue[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    type: '',
    isHost: false,
    searchSelectList: undefined,
  });

  const emits = defineEmits<Emits>();

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();

  const searchSelectData = computed(() => {
    const baseSelectList = [
      {
        name: t('访问入口'),
        id: 'domain',
        multiple: true,
      },
      {
        name: t('集群类型'),
        id: 'cluster_type',
        multiple: true,
        children: [
          {
            id: 'tendbha',
            name: t('主从'),
          },
          {
            id: 'tendbsingle',
            name: t('单节点'),
          },
        ],
      },
      {
        name: t('集群别名'),
        id: 'name',
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
        name: t('管控区域'),
        id: 'bk_cloud_id',
        multiple: true,
        children: props.searchAttrs?.bk_cloud_id,
      },
    ];
    const dbModuleSelect = {
      name: t('所属DB模块'),
      id: 'db_module_id',
      multiple: true,
      children: props.searchAttrs?.db_module_id,
    };
    baseSelectList.splice(3, 0, dbModuleSelect);
    return props.searchSelectList ? props.searchSelectList : baseSelectList;
  });

  const handleSearchChange = (value: ISearchValue[]) => {
    emits('searchValueChange', value);
  };
</script>
