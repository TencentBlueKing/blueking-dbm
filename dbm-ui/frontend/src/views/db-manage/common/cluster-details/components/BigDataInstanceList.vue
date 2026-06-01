<template>
  <div class="big-data-cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <BkButton
        :disabled="isBatchRestartDisabled || isRestartActionDisabled"
        :loading="isBatchRestartLoading"
        style="width: 105px"
        theme="primary"
        @click="handleRestart()">
        {{ t('批量重启') }}
      </BkButton>
      <InstanceBatchCopy
        class="ml-8"
        field="instance_address"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        class="ml-8"
        field="ip"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="instanceTable"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="id"
      selectable
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="instance_address"
        fixed="left"
        :min-width="200"
        :title="t('实例')" />
      <InstanceListFieldColumn
        :cluster-id="clusterData.id"
        :cluster-type="clusterType" />
      <TableColumn
        col-key="action"
        fixed="right"
        :title="t('操作')"
        :width="60">
        <template #default="{ row }: { row: IColumnData }">
          <BkButton
            text
            theme="primary"
            @click="handleRestart(row)">
            {{ t('重启') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>
<script lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import DorisModel from '@services/model/doris/doris';
  import EsModel from '@services/model/es/es';
  import HdfsModel from '@services/model/hdfs/hdfs';
  import KafkaDetailModel from '@services/model/kafka/kafka-detail';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import { createTicket } from '@services/source/ticket';

  import { useInstanceQuickSearch, useTicketMessage, useUrlSearch } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  import { URL_INSTANCE_MEMO_KEY } from '../constants';
  import InstanceListFieldColumn from '../InstanceListFieldColumn.vue';

  interface ClusterTypeRelateClusterModel {
    [ClusterTypes.DORIS]: DorisModel;
    [ClusterTypes.ES]: EsModel;
    [ClusterTypes.HDFS]: HdfsModel;
    [ClusterTypes.KAFKA]: KafkaDetailModel;
    [ClusterTypes.PULSAR]: PulsarModel;
  }

  const clusterTypeWithTicketTypeMap: Record<keyof ClusterTypeRelateClusterModel, TicketTypes> = {
    [ClusterTypes.DORIS]: TicketTypes.DORIS_REBOOT,
    [ClusterTypes.ES]: TicketTypes.ES_REBOOT,
    [ClusterTypes.HDFS]: TicketTypes.HDFS_REBOOT,
    [ClusterTypes.KAFKA]: TicketTypes.KAFKA_REBOOT,
    [ClusterTypes.PULSAR]: TicketTypes.PULSAR_REBOOT,
  };

  type IColumnData = ServiceReturnType<ReturnType<typeof useClusterInstanceList>>['results'][number];
</script>
<script setup lang="tsx" generic="T extends keyof ClusterTypeRelateClusterModel">
  export interface Props<T extends keyof ClusterTypeRelateClusterModel> {
    clusterData: ClusterTypeRelateClusterModel[T];
    clusterType: T;
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const ticketMessage = useTicketMessage();
  const { getSearchParams } = useUrlSearch();

  const requestHandler = useClusterInstanceList(props.clusterType);
  const { handleSelection, selectedList } = useClusterTableSelect<IColumnData>();
  const { quickSearchData, quickSearchValue } = useInstanceQuickSearch({
    cluster_id: props.clusterData.id,
    cluster_type: props.clusterType,
  });

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      ...params,
      cluster_id: props.clusterData.id,
    });

  const instanceTableRef = useTemplateRef('instanceTable');
  const isRestartLoading = ref(false);
  const isBatchRestartLoading = ref(false);
  const isRestartActionDisabled = ref(false);

  const isBatchRestartDisabled = computed(() => selectedList.value.length < 1);

  const getBatchCopyData = () => {
    return instanceTableRef.value!.fetchAllData<IColumnData>();
  };

  const fetchData = () => {
    instanceTableRef.value?.fetchData(quickSearchValue.value);
    // instanceTableRef.value?.clearSelected();
  };

  const handleQuickSearchChange = _.debounce(() => {
    fetchData();
    router.replace({
      query: {
        ...getSearchParams(),
        [URL_INSTANCE_MEMO_KEY]: encodeURIComponent(JSON.stringify(quickSearchValue.value)),
      },
    });
  }, 100);

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const handleRestart = (data?: IColumnData) => {
    const restartInstanceList = data ? [data] : selectedList.value;

    if (data) {
      isRestartLoading.value = true;
    } else {
      isBatchRestartLoading.value = true;
    }

    const formatRequestData = (data: Array<IColumnData>) =>
      data.map((item) => {
        const [ip, port] = item.instance_address.split(':');
        return {
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          instance_id: item.id,
          instance_name: item.instance_name,
          ip,
          port: Number(port),
        };
      });

    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认重启'),
      contentAlign: 'left',
      extCls: 'big-data-instance-replace-model',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onCancel: () => {
        if (data) {
          isRestartLoading.value = false;
        } else {
          isBatchRestartLoading.value = false;
        }
      },
      onConfirm: () => {
        isRestartActionDisabled.value = true;
        return createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            cluster_id: props.clusterData.id,
            instance_list: formatRequestData(restartInstanceList),
          },
          ticket_type: clusterTypeWithTicketTypeMap[props.clusterType],
        })
          .then((data) => {
            ticketMessage(data.id);
            window.changeConfirm = false;
          })
          .finally(() => {
            isRestartActionDisabled.value = false;
            if (data) {
              isRestartLoading.value = false;
            } else {
              isBatchRestartLoading.value = false;
            }
          });
      },
      subTitle: () => (
        <div style='background-color: #F5F7FA; padding: 8px 16px;'>
          <div class='tips-item'>
            {t('实例')} :
            <span
              class='ml-8'
              style='color: #313238'>
              {restartInstanceList.map((instanceItem) => instanceItem.instance_address).join(', ')}
            </span>
          </div>
          <div class='mt-4'>{t('连接将会断开，请谨慎操作！')}</div>
        </div>
      ),
      title: t('确认重启该实例？'),
    });
  };

  onMounted(() => {
    quickSearchValue.value = JSON.parse(decodeURIComponent(String(route.query[URL_INSTANCE_MEMO_KEY] || '{}')));
    fetchData();
  });
</script>
<style lang="less">
  .big-data-cluster-detail-instance-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;
    }
  }

  .big-data-instance-replace-model {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
