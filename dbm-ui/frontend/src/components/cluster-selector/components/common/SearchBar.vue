<template>
  <div class="cluster-selector-search-main">
    <DbQuickSearch
      v-model="searchSelectValue"
      class="search-select-main"
      :data="searchSelectData"
      parse-url
      :placeholder="t('请输入或选择条件搜索')" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { listTag } from '@services/source/tag';

  import type { SearchAttrs } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  export type SearchSelectList = QuickSearchProps['data'];

  interface Props {
    clusterType: ClusterTypes;
    searchAttrs: SearchAttrs;
    searchSelectList?: SearchSelectList;
  }

  const props = withDefaults(defineProps<Props>(), {
    searchSelectList: undefined,
  });

  const searchSelectValue = defineModel<Record<string, string>>({
    default: () => ({}),
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
        name: t('访问入口'),
        type: 'multiple-input',
      },
      {
        id: 'instance',
        name: t('IP 或 IP:Port'),
        type: 'multiple-input',
      },
      {
        id: 'status',
        list: [
          {
            label: t('正常'),
            value: 'normal',
          },
          {
            label: t('异常'),
            value: 'abnormal',
          },
        ],
        name: t('状态'),
        type: 'multiple',
      },
      {
        id: 'name',
        name: t('集群名称'),
        type: 'multiple-input',
      },
      {
        id: 'bk_cloud_id',
        list: (props.searchAttrs?.bk_cloud_id || []).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        name: t('管控区域'),
        type: 'multiple',
      },
    ] as QuickSearchProps['data'];
    if (showDbModuleSelect.value) {
      baseSelectList.splice(3, 0, {
        id: 'db_module_id',
        list: (props.searchAttrs?.db_module_id || []).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        name: t('所属模块'),
        type: 'multiple',
      });
    }

    if (showClusterTypeSelect.value) {
      baseSelectList.splice(3, 0, {
        id: 'cluster_type',
        list: (props.searchAttrs?.cluster_type || []).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        name: t('架构版本'),
        type: 'multiple',
      });
    }
    return [
      ...(props.searchSelectList ? props.searchSelectList : baseSelectList),
      {
        id: 'tag',
        name: t('标签'),
        props: {
          checkStrictly: true,
          showAllLevels: true,
        },
        remoteMethod: () =>
          listTag(
            {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              limit: -1,
              offset: 0,
              type: 'cluster',
            },
            {
              cache: true,
            },
          ).then((data) => {
            const keyValueMap: Record<string, { label: string; value: string }[]> = {};
            data.results.forEach((item) => {
              if (!keyValueMap[item.key]) {
                keyValueMap[item.key] = [];
              }
              keyValueMap[item.key].push({
                label: item.value,
                value: `tag_ids#${item.id}`,
              });
            });

            return Object.keys(keyValueMap).map((tagKey) => ({
              children: keyValueMap[tagKey],
              label: tagKey,
              value: `tag_keys#${tagKey}`,
            }));
          }),
        type: 'multiple-cascader',
      },
    ] as QuickSearchProps['data'];
  });
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
