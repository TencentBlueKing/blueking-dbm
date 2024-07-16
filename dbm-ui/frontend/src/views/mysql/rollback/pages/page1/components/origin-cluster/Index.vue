<template>
  <SmartAction>
    <RenderData
      class="mt16 mb-20"
      @batch-edit="handleBatchEditBackupSource"
      @batch-select-cluster="handleShowBatchSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderData>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
  <ClusterSelector
    v-model:is-show="isShowBatchSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
    @change="handelClusterChange" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import RenderData from './RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './RenderData/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData?.id;
  };

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      window.changeConfirm = true;
    },
  });
  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);

  const tableData = ref<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({ [ClusterTypes.TENDBHA]: [] });

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  const handleBatchEditBackupSource = (obj: Record<string, any>) => {
    if (!obj) {
      return;
    }

    tableData.value.forEach((row) => {
      Object.assign(row, { ...obj });
    });
  };

  // 批量选择
  const handelClusterChange = (selected: Record<string, Array<TendbhaModel>>) => {
    selectedClusters.value = selected;
    const newList = selected[ClusterTypes.TENDBHA].reduce((results, clusterData) => {
      const domain = clusterData.master_domain;
      if (!domainMemo[domain]) {
        const row = createRowData({
          clusterData: {
            id: clusterData.id,
            domain,
            cloudId: clusterData.bk_cloud_id,
            cloudName: clusterData.bk_biz_name,
          },
        });
        results.push(row);
        domainMemo[domain] = true;
      }
      return results;
    }, [] as IDataRow[]);

    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const domain = dataList[index].clusterData?.domain;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
      selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter((item) => item.master_domain !== domain);
    }
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) =>
        createTicket({
          rollback_cluster_type: 'BUILD_INTO_METACLUSTER',
          remark: '',
          details: {
            infos: data,
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLDBRollback',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>
