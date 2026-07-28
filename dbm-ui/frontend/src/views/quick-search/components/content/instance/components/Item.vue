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
          col-key="ip_port"
          fixed="left"
          :min-width="220"
          :title="t('实例')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            <TextOverflowLayout v-if="row.ip_port">
              <BkButton
                text
                theme="primary"
                @click="() => handleToInstance(row)">
                <TextHighlight
                  high-light-color="#FF9C01"
                  :keyword="keyword"
                  :text="row.ip_port" />
              </BkButton>
              <template #append>
                <BkButton
                  class="copy-btn ml-4"
                  text
                  theme="primary"
                  @click="() => handleCopy(row.ip_port)">
                  <DbIcon type="copy" />
                </BkButton>
              </template>
            </TextOverflowLayout>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :title="t('状态')"
          :width="120">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            <ClusterInstanceStatus :data="row.status" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="cluster_domain"
          :min-width="250"
          :title="t('所属集群')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            {{ row.cluster_domain || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="cluster_type"
          :title="t('架构类型')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            {{ row.cluster_type || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="role"
          :title="t('部署角色')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            {{ row.role || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_sub_zone"
          :title="t('园区')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            {{ row.bk_sub_zone || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="bk_biz_id"
          :title="t('所属业务')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
            {{ row.bk_biz_id ? bizIdNameMap[row.bk_biz_id] : '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="creator"
          sortable
          :title="t('主 DBA')">
          <template #default="{ row }: { row: QuickSearchInstanceModel }">
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

  import QuickSearchInstanceModel from '@services/model/quiker-search/quick-search-instance';
  import { quickSearchResult } from '@services/source/quickSearch';

  import { DBTypeInfos, DBTypes, FilterType } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import DbIcon from '@components/db-icon/';
  import { usePagination } from '@components/db-table/hooks/use-pagination.ts';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import { PrimaryTable } from '@components/tdesign-ui/table';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, exportExcelFile } from '@utils';

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
    results: [] as QuickSearchInstanceModel[],
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
      resource_type: 'instance',
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
    return results as QuickSearchInstanceModel[];
  };

  const fetchData = (params?: Record<string, any>, loading = true) => {
    if (props.formData.resource_types.length > 0 && !props.formData.resource_types.includes('instance')) {
      return;
    }
    pagination.current = 1;
    fetchListData(loading);
  };

  const handleClearFilter = () => {
    fetchData();
    emits('clear-search');
  };

  const handleCopy = (content: string) => {
    execCopy(content, t('复制成功，共n条', { n: 1 }));
  };

  const handleToInstance = (data: QuickSearchInstanceModel) => {
    handleRedirect(
      data.cluster_type,
      {
        instance: data.instance,
      },
      data.bk_biz_id,
    );
  };

  const handleExport = async () => {
    const dataList = await fetchAllData();
    const formatData = dataList.map((dataItem) =>
      Object.fromEntries(
        [
          { label: t('实例'), value: dataItem.ip_port },
          { label: t('状态'), value: dataItem.status },
          { label: t('所属集群'), value: dataItem.cluster_domain },
          { label: t('架构类型'), value: dataItem.cluster_type },
          { label: t('部署角色'), value: dataItem.role },
          { label: t('园区'), value: dataItem.bk_sub_zone },
          { label: t('所属业务'), value: String(dataItem.bk_biz_id) },
          { label: t('业务名称'), value: props.bizIdNameMap[dataItem.bk_biz_id] },
          { label: t('主 DBA'), value: dataItem.dba },
        ].map(({ label, value }) => [label, value]),
      ),
    );
    const colsWidths = [
      { width: 24 },
      { width: 16 },
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
