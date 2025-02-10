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
          :pagination="pagination[index]">
          <BkTableColumn
            field="ip_port"
            :label="t('实例')"
            :min-width="220">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              <TextOverflowLayout v-if="rowData.ip_port">
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleToInstance(rowData)">
                  <HightLightText
                    high-light-color="#FF9C01"
                    :key-word="keyword"
                    :text="rowData.ip_port" />
                </BkButton>
                <template #append>
                  <BkButton
                    class="ml-4"
                    text
                    theme="primary"
                    @click="() => handleCopy(rowData.ip_port)">
                    <DbIcon type="copy" />
                  </BkButton>
                </template>
              </TextOverflowLayout>
              <span v-else>--</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="status"
            :label="t('状态')">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              <ClusterInstanceStatus :data="rowData.status" />
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="cluster_domain"
            :label="t('所属集群')"
            :min-width="250">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              {{ rowData.cluster_domain || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="cluster_type"
            :label="t('架构类型')">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              {{ rowData.cluster_type || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="role"
            :label="t('部署角色')">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              {{ rowData.role || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_sub_zone"
            :label="t('园区')">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              {{ rowData.bk_sub_zone || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_biz_id"
            :label="t('所属业务')">
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
              {{ rowData.bk_biz_id ? bizIdNameMap[rowData.bk_biz_id] : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="creator"
            :label="t('主 DBA')"
            sortable>
            <template #default="{data: rowData}: {data: QuickSearchInstanceModel}">
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

  import QuickSearchInstanceModel from '@services/model/quiker-search/quick-search-instance';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  import { groupByDbType } from '../common/utils';

  import { exportExcelFile } from '@/utils';

  interface Props {
    keyword: string;
    data: QuickSearchInstanceModel[];
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
    }[]
  >([]);

  const renderData = computed(() => groupByDbType<QuickSearchInstanceModel>(props.data));

  watch(
    renderData,
    (newRenderData) => {
      pagination.value = newRenderData.dataList.map((dataItem) => ({
        count: dataItem.dataList.length,
        limit: 10,
      }));
    },
    {
      immediate: true,
    },
  );

  const handleExport = (clusterType: string, dataList: QuickSearchInstanceModel[]) => {
    const formatData = dataList.map((dataItem) => ({
      ['IP']: dataItem.ip,
      [t('IP端口')]: String(dataItem.port),
      [t('实例角色')]: dataItem.role,
      [t('城市')]: dataItem.bk_idc_area,
      [t('机房')]: dataItem.bk_idc_name,
      [t('集群ID')]: dataItem.cluster_id,
      [t('集群类型')]: dataItem.cluster_type,
      [t('主域名')]: dataItem.cluster_domain,
      [t('主版本')]: dataItem.major_version,
      [t('业务ID')]: String(dataItem.bk_biz_id),
      [t('业务名称')]: props.bizIdNameMap[dataItem.bk_biz_id],
      [t('主 DBA')]: dataItem.dba,
    }));
    const colsWidths = [
      { width: 10 },
      { width: 10 },
      { width: 16 },
      { width: 24 },
      { width: 20 },
      { width: 10 },
      { width: 10 },
      { width: 10 },
      { width: 16 },
      { width: 16 },
      { width: 24 },
      { width: 24 },
      { width: 16 },
      { width: 10 },
      { width: 16 },
    ];

    exportExcelFile(formatData, colsWidths, clusterType, `${clusterType}.xlsx`);
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
  }
</style>
