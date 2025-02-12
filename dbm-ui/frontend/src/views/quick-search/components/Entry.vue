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
          }">
          <BkTableColumn
            field="entry"
            :label="t('访问入口（域名、CLB、北极星）')"
            :min-width="250">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              <TextOverflowLayout>
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleToCluster(rowData)">
                  <HightLightText
                    high-light-color="#FF9C01"
                    :key-word="formattedKeyword"
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
          </BkTableColumn>
          <BkTableColumn
            field="cluster_status"
            :label="t('状态')"
            :width="100">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              <RenderClusterStatus :data="rowData.cluster_status" />
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="immute_domain"
            :label="t('所属集群')"
            :min-width="250">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              {{ rowData.immute_domain || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="cluster_type"
            :label="t('架构类型')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              {{ rowData.cluster_type || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="major_version"
            :label="t('版本')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              {{ rowData.major_version || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="region"
            :label="t('地域')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              {{ rowData.region || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_biz_id"
            :label="t('所属业务')"
            :width="150">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              {{ rowData.bk_biz_id ? bizIdNameMap[rowData.bk_biz_id] : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="disaster_tolerance_level"
            :label="t('容灾要求')">
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
              {{ rowData.disaster_tolerance_level || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="creator"
            :label="t('主 DBA')"
            sortable>
            <template #default="{data: rowData}: {data: QuickSearchEntryModel}">
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

  import QuickSearchEntryModel from '@services/model/quiker-search/quick-search-entry';

  import { batchSplitRegex } from '@common/regex';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, exportExcelFile } from '@utils';

  import { groupByDbType } from '../common/utils';

  interface Props {
    keyword: string;
    data: QuickSearchEntryModel[];
    bizIdNameMap: Record<number, string>;
    isAnomalies: boolean;
    isSearching: boolean;
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

  const renderData = computed(() => groupByDbType<QuickSearchEntryModel>(props.data));

  watch(
    renderData,
    (newRenderData) => {
      console.log('renderData = ', renderData);
      pagination.value = newRenderData.dataList.map((dataItem) => ({
        count: dataItem.dataList.length,
        limit: 10,
        current: 1,
        remote: false,
      }));
    },
    {
      immediate: true,
    },
  );

  const handleExport = (clusterType: string, dataList: QuickSearchEntryModel[]) => {
    const formatData = dataList.map((dataItem) => ({
      [t('集群ID')]: String(dataItem.id),
      [t('访问入口（域名、CLB、北极星）')]: dataItem.entry,
      [t('所属集群')]: dataItem.immute_domain,
      [t('架构类型')]: dataItem.cluster_type,
      [t('版本')]: dataItem.major_version,
      [t('地域')]: dataItem.region,
      [t('所属业务')]: String(dataItem.bk_biz_id),
      [t('业务名称')]: props.bizIdNameMap[dataItem.bk_biz_id],
      [t('容灾要求')]: dataItem.disaster_tolerance_level,
      [t('主 DBA')]: dataItem.dba,
    }));
    const colsWidths = [{ width: 10 }, { width: 16 }, { width: 16 }, { width: 24 }, { width: 24 }, { width: 16 }];

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
  @import '../style/table-card.less';

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
  }
</style>
