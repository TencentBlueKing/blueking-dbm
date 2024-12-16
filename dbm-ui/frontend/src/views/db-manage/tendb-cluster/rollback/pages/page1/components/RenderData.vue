<template>
  <SmartAction>
    <RenderTable
      :key="rollbackClusterType"
      class="mt16 mb-20"
      :rollback-cluster-type="rollbackClusterType"
      @batch-edit="(obj) => handleBatchEdit(obj)"
      @show-selector="handleShowSelector">
      <RenderRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        :rollback-cluster-type="rollbackClusterType"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="() => handleRemove(index)" />
    </RenderTable>
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
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script lang="ts">
  const enum RollbackClusterTypes {
    BUILD_INTO_NEW_CLUSTER = 'BUILD_INTO_NEW_CLUSTER',
    BUILD_INTO_EXIST_CLUSTER = 'BUILD_INTO_EXIST_CLUSTER',
    BUILD_INTO_METACLUSTER = 'BUILD_INTO_METACLUSTER',
  }

  interface Props {
    data: IDataRow[];
    rollbackClusterType: RollbackClusterTypes;
  }

  interface Exposes {
    reset: () => void;
  }
</script>
<script setup lang="ts">
  import { debounce } from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import { messageWarn } from '@utils';

  import RenderRow, { createRowData, type IDataRow } from './render-row/Index.vue';
  import RenderTable from './RenderTable.vue';

  const props = defineProps<Props>();

  const { t } = useI18n();

  const router = useRouter();

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};
  const initSelected = {
    [ClusterTypes.TENDBCLUSTER]: [] as TendbClusterModel[],
  };

  const rowRefs = ref();
  const isShowSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData({})]);
  const selectedClusters = shallowRef<{ [key: string]: Array<TendbClusterModel> }>(initSelected);

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.TENDBCLUSTER]: {
          // 仅有构造到新集群为单选
          multiple: props.rollbackClusterType !== RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER,
          getResourceList: getTendbClusterList,
          disabledRowConfig:
            props.rollbackClusterType !== RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER
              ? [
                  {
                    handler: (data: TendbClusterModel) => data.isTemporary,
                    tip: t('不能选择临时集群'),
                  },
                ]
              : [],
        },
      }) as unknown as Record<string, TabConfig>,
  );

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData?.id;
  };

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  // 批量编辑
  const handleBatchEdit = (obj: Record<string, any>) => {
    if (checkListEmpty(tableData.value)) {
      debounce(() => {
        messageWarn(t('请先添加待回档集群'));
      }, 300);
      return;
    }
    if (!obj) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, { ...obj });
    });
    const field = Object.keys(obj)[0] as keyof IDataRow;
    if (['databases', 'tables', 'databasesIgnore', 'tablesIgnore'].includes(field)) {
      nextTick(() => {
        Promise.all(rowRefs.value.map((item: { validator: (field: keyof IDataRow) => void }) => item.validator(field)));
      });
    }
  };

  // 批量选择
  const handelClusterChange = (selected: Record<string, Array<TendbClusterModel>>) => {
    selectedClusters.value = selected;
    const newList = selected[ClusterTypes.TENDBCLUSTER].reduce((results, clusterData) => {
      const domain = clusterData.master_domain;
      if (!domainMemo[domain]) {
        const row = createRowData({
          clusterData: {
            id: clusterData.id,
            domain,
            cloudId: clusterData.bk_cloud_id,
            cloudName: clusterData.bk_biz_name,
            clusterType: clusterData.cluster_type,
          },
        });
        results.push(row);
        if (props.rollbackClusterType !== RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER) {
          domainMemo[domain] = true;
        }
      }
      return results;
    }, [] as IDataRow[]);
    if (props.rollbackClusterType === RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER || checkListEmpty(tableData.value)) {
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
    const rowData = dataList[index].clusterData;
    if (rowData?.domain && rowData?.clusterType) {
      delete domainMemo[rowData.domain];
      const clustersArr = selectedClusters.value[rowData.clusterType];
      selectedClusters.value[rowData.clusterType] = clustersArr.filter((item) => item.master_domain !== rowData.domain);
    }
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
      await createTicket({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ticket_type: TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER,
        remark: '',
        details: {
          rollback_cluster_type: props.rollbackClusterType,
          infos,
        },
      }).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'spiderRollback',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value = initSelected;
    domainMemo = {};
    window.changeConfirm = false;
  };

  watch(
    () => props.data,
    () => {
      tableData.value = props.data;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    reset() {
      handleReset();
    },
  });
</script>
