<template>
  <DbCard
    v-if="tableData.count > 0"
    class="search-result-cluster search-result-card"
    mode="collapse"
    :title="DBTypeInfos[dbType].name">
    <template #desc>
      <I18nT
        class="ml-8"
        keypath="共n条"
        style="color: #63656e"
        tag="span">
        <template #n>
          <strong>{{ tableData.count }}</strong>
        </template>
      </I18nT>
      <BkButton
        v-if="tableData.count > 0"
        class="ml-8"
        text
        theme="primary"
        @click.stop="handleExport">
        <DbIcon
          class="export-button-icon"
          type="daochu" />
        <span class="export-button-text">{{ t('导出') }}</span>
      </BkButton>
    </template>
    <BkLoading :loading="isLoading">
      <PrimaryTable
        ref="bkTableRef"
        class="mt-14"
        :data="tableData.results"
        ellipsis
        :max-height="400"
        resizable
        row-key="id"
        show-header
        title-ellipsis>
        <TableColumn
          col-key="entry"
          fixed="left"
          :min-width="250"
          :title="t('集群')">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            <TextOverflowLayout>
              <BkButton
                text
                theme="primary"
                @click="() => handleToCluster(row)">
                <TextHighlight
                  high-light-color="#FF9C01"
                  :keyword="formattedKeyword"
                  :text="row.displayValue" />
              </BkButton>
              <template #append>
                <BkButton
                  class="copy-btn ml-4"
                  text
                  theme="primary"
                  @click="() => handleCopy(row.displayValue)">
                  <DbIcon type="copy" />
                </BkButton>
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TagColumn
          :filter-type="formData.filter_type"
          :keyword="keyword" />
        <ClusterEnrtyColumn
          :filter-type="formData.filter_type"
          :keyword="keyword" />
        <TableColumn
          col-key="cluster_status"
          :title="t('状态')"
          :width="100">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            <RenderClusterStatus :data="row.status" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="cluster_type"
          :title="t('架构类型')"
          :width="150">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            {{ row.cluster_type || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="major_version"
          :title="t('版本')"
          :width="150">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            {{ row.major_version || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="region"
          :title="t('地域')"
          :width="150">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            {{ row.region || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_biz_id"
          :title="t('所属业务')"
          :width="150">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            {{ row.bk_biz_id ? bizIdNameMap[row.bk_biz_id] : '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="disaster_tolerance_level"
          :title="t('容灾要求')">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            {{ row.disasterToleranceLevelName || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="creator"
          sortable
          :title="t('主 DBA')">
          <template #default="{ row }: { row: QuickSearchClusterModel }">
            {{ row.dba || '--' }}
          </template>
        </TableColumn>
        <template #empty>
          <EmptyStatus
            :is-anomalies="isRequestFailed"
            is-searching
            @clear-search="handleClearFilter"
            @refresh="fetchListData" />
        </template>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          @change="handlePageValueChange"
          @limit-change="handlePageLimitChange" />
      </div>
    </BkLoading>
  </DbCard>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';
  import { quickSearchResult } from '@services/source/quickSearch';

  import { DBTypeInfos, DBTypes, FilterType } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import DbIcon from '@components/db-icon/';
  import { usePagination } from '@components/db-table/hooks/use-pagination.ts';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import { PrimaryTable } from '@components/tdesign-ui/table';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, exportExcelFile } from '@utils';

  import ClusterEnrtyColumn from './table/ClusterEnrtyColumn.vue';
  import TagColumn from './table/TagColumn.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    dbType: DBTypes;
    formData: {
      bk_biz_ids: number[];
      db_types: string[];
      filter_type: FilterType;
      resource_types: string[];
    };
    keyword: string;
  }

  interface Exposed {
    fetchData: () => void;
    getCount: () => number;
  }

  type Emits = (e: 'clear-search') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const handleRedirect = useRedirect();

  const isLoading = ref(false);
  const tableData = ref({
    count: 0,
    next: '',
    permission: {},
    previous: '',
    results: [] as QuickSearchClusterModel[],
  });

  const {
    onChange: handlePageValueChange,
    onLimitChange: handlePageLimitChange,
    pagination,
  } = usePagination({
    callback: () => {
      fetchListData();
    },
  });

  const isRequestFailed = ref(false);

  const getParams = () => {
    return {
      ...props.formData,
      db_types: [props.dbType],
      keyword: props.keyword.replace(batchSplitRegex, ' '),
      resource_type: 'cluster',
    };
  };

  const fetchListData = (loading = true) => {
    Promise.resolve().then(() => {
      isLoading.value = loading;
      const params = {
        ...getParams(),
        limit: pagination.limit,
        offset: (pagination.current - 1) * pagination.limit,
      };
      isRequestFailed.value = false;
      quickSearchResult(params)
        .then((data: any) => {
          tableData.value = data;
          pagination.count = data.count;
          isRequestFailed.value = false;
        })
        .catch(() => {
          tableData.value.results = [];
          pagination.count = 0;
          isRequestFailed.value = true;
        })
        .finally(() => {
          isLoading.value = false;
        });
    });
  };

  // 拉取全量数据
  const fetchAllData = async () => {
    const { results } = await quickSearchResult({
      ...getParams(),
      limit: -1,
      offset: 0,
    });
    return results as QuickSearchClusterModel[];
  };

  const fetchData = (params?: Record<string, any>, loading = true) => {
    if (props.formData.resource_types.length > 0 && !props.formData.resource_types.includes('cluster')) {
      return;
    }
    pagination.current = 1;
    fetchListData(loading);
  };

  const handleClearFilter = () => {
    fetchData();
    emits('clear-search');
  };

  const formattedKeyword = computed(() =>
    props.keyword
      .split(batchSplitRegex)
      .map((item) => {
        if (item.includes(':')) {
          return item.split(':')[0];
        }
        return item;
      })
      .join(' '),
  );

  const handleCopy = (content: string) => {
    execCopy(content, t('复制成功，共n条', { n: 1 }));
  };

  const handleToCluster = (data: QuickSearchClusterModel) => {
    handleRedirect(
      data.cluster_type,
      {
        domain: data.displayValue,
      },
      data.bk_biz_id,
    );
  };

  const handleExport = async () => {
    const dataList = await fetchAllData();
    const formatData = dataList.map((dataItem) =>
      Object.fromEntries(
        [
          { label: t('集群'), value: dataItem.displayValue },
          { label: t('标签'), value: dataItem.tags.map((tagItem) => `${tagItem.key}:${tagItem.value}`).join('\n') },
          { label: t('访问入口'), value: dataItem.dispalyEntryList.map((entryItem) => entryItem.entry).join('\n') },
          { label: t('架构类型'), value: dataItem.cluster_type },
          { label: t('版本'), value: dataItem.major_version },
          { label: t('地域'), value: dataItem.region },
          { label: t('所属业务'), value: String(dataItem.bk_biz_id) },
          { label: t('业务名称'), value: props.bizIdNameMap[dataItem.bk_biz_id] },
          { label: t('容灾要求'), value: dataItem.disasterToleranceLevelName },
          { label: t('主 DBA'), value: dataItem.dba },
        ].map(({ label, value }) => [label, value]),
      ),
    );
    const colsWidths = [
      { width: 24 },
      { width: 16 },
      { width: 24 },
      { width: 24 },
      { width: 24 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
    ];

    exportExcelFile(formatData, colsWidths, props.dbType, `${props.dbType}.xlsx`);
  };

  onMounted(() => {
    fetchData();
  });

  onActivated(() => {
    fetchData();
  });

  defineExpose<Exposed>({
    fetchData,
    getCount: () => tableData.value.count,
  });
</script>

<style lang="less" scoped>
  @import '../../table-card.less';

  .search-result-cluster {
    .export-button-icon {
      font-size: 14px;
    }

    .export-button-text {
      margin-left: 4px;
      font-size: 12px;
    }

    tr {
      .copy-btn {
        display: none;
      }

      &:hover {
        .copy-btn {
          display: inline-block;
        }
      }
    }
  }

  .table-footer {
    position: relative;
    z-index: 1;
    display: flex;
    height: 60px;
    padding: 0 16px;
    margin-top: -1px;
    background: #fff;
    border-top: 1px solid var(--td-component-border);
    align-items: center;

    .bk-pagination {
      width: 100%;

      & > .is-last {
        margin-left: auto;
      }
    }
  }
</style>
