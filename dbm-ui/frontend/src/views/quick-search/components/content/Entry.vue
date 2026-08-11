<template>
  <div :key="settingChangeKey">
    <template v-if="renderData.dataList.length">
      <DbCard
        v-for="(item, index) in renderData.dataList"
        :key="item.dbType"
        class="search-result-cluster search-result-card"
        mode="collapse"
        :title="item.dbType">
        <template #desc>
          <I18nT
            class="ml-8"
            keypath="共n条"
            style="color: #63656e"
            tag="span">
            <template #n>
              <strong>{{ item.dataList.length }}</strong>
            </template>
          </I18nT>
          <BkButton
            class="ml-8"
            text
            theme="primary"
            @click.stop="handleExport(item.dbType, item.dataList)">
            <DbIcon
              class="export-button-icon"
              type="daochu" />
            <span class="export-button-text">{{ t('导出') }}</span>
          </BkButton>
        </template>
        <PrimaryTable
          class="search-result-table mt-14"
          :data="getTableData(item.dataList, index)"
          row-key="id">
          <TableColumn
            col-key="entry"
            :min-width="250"
            :title="t('访问入口')">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              <TextOverflowLayout>
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleToCluster(rowData)">
                  <TextHighlight
                    high-light-color="#FF9C01"
                    :keyword="formattedKeyword"
                    :text="rowData.entry" />
                </BkButton>
                <template #append>
                  <BkTag
                    v-if="rowData.cluster_entry_type === 'clb'"
                    class="redis-cluster-clb"
                    size="small">
                    CLB
                  </BkTag>
                  <BkTag
                    v-if="rowData.cluster_entry_type === 'polaris'"
                    class="redis-cluster-polary"
                    size="small">
                    {{ t('北极星') }}
                  </BkTag>
                  <BkTag
                    v-if="rowData.role === 'master_entry'"
                    size="small"
                    theme="info">
                    {{ t('主') }}
                  </BkTag>
                  <BkTag
                    v-if="rowData.role === 'slave_entry'"
                    size="small"
                    theme="success">
                    {{ t('从') }}
                  </BkTag>
                  <BkButton
                    class="copy-btn ml-4"
                    text
                    theme="primary"
                    @click="() => handleCopy(rowData.entry)">
                    <DbIcon type="copy" />
                  </BkButton>
                </template>
              </TextOverflowLayout>
            </template>
          </TableColumn>
          <TableColumn
            col-key="cluster_status"
            :title="t('状态')"
            :width="100">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              <RenderClusterStatus :data="rowData.cluster_status" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="immute_domain"
            :min-width="250"
            :title="t('所属集群')">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.immute_domain || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="cluster_type"
            :title="t('架构类型')"
            :width="150">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.cluster_type || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="major_version"
            :title="t('版本')"
            :width="150">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.major_version || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="region"
            :title="t('地域')"
            :width="150">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.region || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="bk_biz_id"
            :title="t('所属业务')"
            :width="150">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.bk_biz_id ? bizIdNameMap[rowData.bk_biz_id] : '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="disaster_tolerance_level"
            :title="t('容灾要求')">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.disasterToleranceLevelName || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="creator"
            sorter
            :title="t('主 DBA')">
            <template #default="{ row: rowData }: { row: QuickSearchEntryModel }">
              {{ rowData.dba || '--' }}
            </template>
          </TableColumn>
        </PrimaryTable>
        <div class="table-footer mb-8">
          <BkPagination
            v-bind="pagination[index]"
            :layout="['total', 'limit', 'list']"
            :model-value="pagination[index].current"
            @change="(value: number) => handlePageValueChange(value, index)"
            @limit-change="(value: number) => handlePageLimitChange(value, index)" />
        </div>
      </DbCard>
    </template>
    <EmptyStatus
      v-else
      class="empty-status"
      :is-anomalies="isAnomalies"
      :is-searching="isSearching"
      @clear-search="handleClearSearch"
      @refresh="handleRefresh" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import QuickSearchEntryModel from '@services/model/quiker-search/quick-search-entry';

  import { batchSplitRegex } from '@common/regex';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, exportExcelFile } from '@utils';

  import { groupByDbType } from './utils';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: QuickSearchEntryModel[];
    isAnomalies: boolean;
    isSearching: boolean;
    keyword: string;
  }

  interface Emits {
    (e: 'refresh'): void;
    (e: 'clearSearch'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const handleRedirect = useRedirect();

  const settingChangeKey = ref(1);
  const pagination = ref<
    {
      count: number;
      current: number;
      limit: number;
    }[]
  >([]);

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

  const renderData = computed(() => groupByDbType<QuickSearchEntryModel>(props.data));

  watch(
    renderData,
    (newRenderData) => {
      pagination.value = newRenderData.dataList.map((dataItem) => ({
        count: dataItem.dataList.length,
        current: 1,
        limit: 10,
      }));
    },
    {
      immediate: true,
    },
  );

  const getTableData = (dataList: QuickSearchEntryModel[], index: number) => {
    const { current, limit } = pagination.value[index];
    return dataList.slice((current - 1) * limit, current * limit);
  };

  const handlePageValueChange = (value: number, index: number) => {
    pagination.value[index].current = value;
  };

  const handlePageLimitChange = (value: number, index: number) => {
    pagination.value[index].limit = value;
    pagination.value[index].current = 1;
  };

  const handleExport = (clusterType: string, dataList: QuickSearchEntryModel[]) => {
    const formatData = dataList.map((dataItem) =>
      Object.fromEntries(
        [
          { label: t('集群ID'), value: String(dataItem.id) },
          { label: t('访问入口（域名、CLB、北极星）'), value: dataItem.entry },
          { label: t('所属集群'), value: dataItem.immute_domain },
          { label: t('架构类型'), value: dataItem.cluster_type },
          { label: t('版本'), value: dataItem.major_version },
          { label: t('地域'), value: dataItem.region },
          { label: t('所属业务'), value: String(dataItem.bk_biz_id) },
          { label: t('业务名称'), value: props.bizIdNameMap[dataItem.bk_biz_id] },
          { label: t('容灾要求'), value: dataItem.disaster_tolerance_level },
          { label: t('主 DBA'), value: dataItem.dba },
        ].map(({ label, value }) => [label, value]),
      ),
    );
    const colsWidths = [
      { width: 10 },
      { width: 16 },
      { width: 16 },
      { width: 24 },
      { width: 24 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
      { width: 16 },
    ];

    exportExcelFile(formatData, colsWidths, clusterType, `${clusterType}.xlsx`);
  };

  const handleCopy = (content: string) => {
    execCopy(content, t('复制成功，共n条', { n: 1 }));
  };

  const handleToCluster = (data: QuickSearchEntryModel) => {
    handleRedirect(
      data.cluster_type,
      {
        domain: data.entry,
      },
      data.bk_biz_id,
    );
  };

  const handleRefresh = () => {
    emits('refresh');
  };

  const handleClearSearch = () => {
    emits('clearSearch');
  };
</script>

<style lang="less" scoped>
  @import './table-card.less';

  .search-result-cluster {
    .export-button-icon {
      font-size: 14px;
    }

    .export-button-text {
      margin-left: 4px;
      font-size: 12px;
    }

    .redis-cluster-clb {
      color: #8e3aff;
      cursor: pointer;
      background-color: #f2edff;

      &:hover {
        color: #8e3aff;
        background-color: #e3d9fe;
      }
    }

    .redis-cluster-polary {
      color: #3a84ff;
      cursor: pointer;
      background-color: #edf4ff;

      &:hover {
        color: #3a84ff;
        background-color: #e1ecff;
      }
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

    .table-footer {
      display: flex;
      align-items: center;

      .bk-pagination {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }
  }
</style>
