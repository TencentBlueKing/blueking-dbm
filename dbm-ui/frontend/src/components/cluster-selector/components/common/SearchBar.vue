<template>
  <DbSearchSelect
    class="mb-16"
    :data="searchSelectData"
    :model-value="searchSelectValue"
    :placeholder="t('请输入或选择条件搜索')"
    unique-select
    @change="handleSearchChange" />
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  import { ClusterTypes } from '@common/const';

  export type SearchSelectList = {
    id: string;
    name: string;
    children?: {
      id: string | number;
      name: string;
    }[];
  }[];

  interface Props {
    clusterType: ClusterTypes;
    searchAttrs: SearchAttrs;
    searchSelectList?: SearchSelectList;
    // placeholder?: string
  }

  interface Emits {
    (e: 'searchValueChange', value: ISearchValue[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    searchSelectList: undefined,
    placeholder: '',
  });

  const emits = defineEmits<Emits>();

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();

  const showDbModuleSelect = computed(() =>
    [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE, ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.SQLSERVER_HA].includes(
      props.clusterType,
    ),
  );

  const showClusterTypeSelect = computed(() => props.clusterType === ClusterTypes.REDIS);

  const searchSelectData = computed(() => {
    const baseSelectList = [
      {
        name: t('访问入口'),
        id: 'domain',
        multiple: true,
      },
      {
        name: t('IP 或 IP:Port'),
        id: 'instance',
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
        children: props.searchAttrs?.bk_cloud_id,
      },
    ];
    if (showDbModuleSelect.value) {
      const dbModuleSelect = {
        name: t('所属模块'),
        id: 'db_module_id',
        multiple: true,
        children: props.searchAttrs?.db_module_id,
      };
      baseSelectList.splice(3, 0, dbModuleSelect);
    }

    console.log('架构版本');
    if (showClusterTypeSelect.value) {
      const clusterTypeSelect = {
        name: t('架构版本'),
        id: 'cluster_type',
        multiple: true,
        children: props.searchAttrs?.cluster_type,
      };
      baseSelectList.splice(3, 0, clusterTypeSelect);
    }
    return props.searchSelectList ? props.searchSelectList : baseSelectList;
  });

  const handleSearchChange = (value: ISearchValue[]) => {
    emits('searchValueChange', value);
  };
</script>
