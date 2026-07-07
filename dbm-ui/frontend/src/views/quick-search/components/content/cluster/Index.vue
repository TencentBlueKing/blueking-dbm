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
        <BkTable
          class="search-result-table mt-14 mb-8"
          :data="item.dataList"
          :pagination="pagination[index]"
          :row-config="{
            useKey: true,
            keyField: 'id',
          }"
          :show-overflow="false">
          <BkTableColumn
            field="entry"
            fixed="left"
            :label="t('集群')"
            :min-width="250">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              <TextOverflowLayout>
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleToCluster(rowData)">
                  <TextHighlight
                    high-light-color="#FF9C01"
                    :keyword="formattedKeyword"
                    :text="rowData.displayValue" />
                </BkButton>
                <template #append>
                  <BkButton
                    class="copy-btn ml-4"
                    text
                    theme="primary"
                    @click="() => handleCopy(rowData.displayValue)">
                    <DbIcon type="copy" />
                  </BkButton>
                </template>
              </TextOverflowLayout>
            </template>
          </BkTableColumn>
          <TagColumn
            :filter-type="filterType"
            :keyword="keyword" />
          <ClusterEnrtyColumn
            :filter-type="filterType"
            :keyword="keyword" />
          <BkTableColumn
            field="cluster_status"
            :label="t('状态')"
            :width="100">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              <RenderClusterStatus :data="rowData.status" />
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="cluster_type"
            :label="t('架构类型')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              {{ rowData.cluster_type || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="major_version"
            :label="t('版本')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              {{ rowData.major_version || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="region"
            :label="t('地域')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              {{ rowData.region || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_biz_id"
            :label="t('所属业务')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              {{ rowData.bk_biz_id ? bizIdNameMap[rowData.bk_biz_id] : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="disaster_tolerance_level"
            :label="t('容灾要求')">
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              {{ rowData.disasterToleranceLevelName || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="creator"
            :label="t('主 DBA')"
            sortable>
            <template #default="{data: rowData}: {data: QuickSearchClusterModel}">
              {{ rowData.dba || '--' }}
            </template>
          </BkTableColumn>
        </BkTable>
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

  import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';

  import { FilterType } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, exportExcelFile } from '@utils';

  import { groupByDbType } from '../utils';

  import ClusterEnrtyColumn from './components/ClusterEnrtyColumn.vue';
  import TagColumn from './components/TagColumn.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: QuickSearchClusterModel[];
    filterType: FilterType;
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
      limit: number;
      remote: false;
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

  const renderData = computed(() => groupByDbType<QuickSearchClusterModel>(props.data));

  watch(
    renderData,
    (newRenderData) => {
      pagination.value = newRenderData.dataList.map((dataItem) => ({
        count: dataItem.dataList.length,
        current: 1,
        limit: 10,
        remote: false,
      }));
    },
    {
      immediate: true,
    },
  );

  const handleExport = (clusterType: string, dataList: QuickSearchClusterModel[]) => {
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

    exportExcelFile(formatData, colsWidths, clusterType, `${clusterType}.xlsx`);
  };

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

  const handleRefresh = () => {
    emits('refresh');
  };

  const handleClearSearch = () => {
    emits('clearSearch');
  };
</script>

<style lang="less" scoped>
  @import '../table-card.less';

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
</style>
