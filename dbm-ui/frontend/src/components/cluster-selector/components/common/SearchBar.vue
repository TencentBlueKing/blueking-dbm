<template>
  <div class="cluster-selector-search-main">
    <TagSearch @search="handleTagSearch" />
    <DbSearchSelect
      class="search-select-main"
      :data="searchSelectData"
      :model-value="searchSelectValue"
      :placeholder="t('请输入或选择条件搜索')"
      unique-select
      @change="handleSearchChange" />
  </div>
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import TagSearch, { type TagSearchValue } from '@components/tag-search/index.vue';

  export type SearchSelectList = {
    children?: {
      id: string | number;
      name: string;
    }[];
    id: string;
    name: string;
  }[];

  interface Props {
    clusterType: ClusterTypes;
    searchAttrs: SearchAttrs;
    searchSelectList?: SearchSelectList;
  }

  interface Emits {
    (e: 'searchValueChange', value: ISearchValue[]): void;
    (e: 'tagValueChange', value: TagSearchValue): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    searchSelectList: undefined,
  });

  const emits = defineEmits<Emits>();

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();

  const showDbModuleSelect = computed(() =>
    [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE].includes(
      props.clusterType,
    ),
  );

  const showClusterTypeSelect = computed(() => props.clusterType === ClusterTypes.REDIS);

  const searchSelectData = computed(() => {
    const baseSelectList = [
      {
        id: 'domain',
        multiple: true,
        name: t('访问入口'),
      },
      {
        id: 'instance',
        multiple: true,
        name: t('IP 或 IP:Port'),
      },
      {
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
        id: 'status',
        multiple: true,
        name: t('状态'),
      },
      {
        id: 'name',
        multiple: true,
        name: t('集群名称'),
      },
      {
        children: props.searchAttrs?.bk_cloud_id,
        id: 'bk_cloud_id',
        multiple: true,
        name: t('管控区域'),
      },
    ];
    if (showDbModuleSelect.value) {
      const dbModuleSelect = {
        children: props.searchAttrs?.db_module_id,
        id: 'db_module_id',
        multiple: true,
        name: t('所属模块'),
      };
      baseSelectList.splice(3, 0, dbModuleSelect);
    }

    if (showClusterTypeSelect.value) {
      const clusterTypeSelect = {
        children: props.searchAttrs?.cluster_type,
        id: 'cluster_type',
        multiple: true,
        name: t('架构版本'),
      };
      baseSelectList.splice(3, 0, clusterTypeSelect);
    }
    return props.searchSelectList ? props.searchSelectList : baseSelectList;
  });

  const handleSearchChange = (value: ISearchValue[]) => {
    emits('searchValueChange', value);
  };

  const handleTagSearch = (value: TagSearchValue) => {
    emits('tagValueChange', value);
  };
</script>
<style lang="less">
  .cluster-selector-search-main {
    display: flex;
    width: 100%;
    gap: 8px;
    margin-bottom: 16px;

    .search-select-main {
      flex: 1;
    }
  }
</style>
