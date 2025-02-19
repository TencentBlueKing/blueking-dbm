<template>
  <div>
    <BkForm
      class="mt-20"
      form-type="vertical">
      <BkFormItem
        :label="t('时区')"
        required>
        <TimeZonePicker style="width: 450px" />
      </BkFormItem>
    </BkForm>
    <RenderData
      class="mt16"
      @batch-select-cluster="handleShowBatchSelector"
      @batch-select-target-cluster="handleShowBatchTargetSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderData>
    <ClusterSelector
      v-model:is-show="isShowBatchSrcSelector"
      :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
      :selected="selectedSrcClusters"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import RenderData from './components/RenderData.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/Row.vue';

  interface Expose {
    reset: () => void;
    submit: () => Promise<any>;
  }

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  const { t } = useI18n();

  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>();
  const isShowBatchSrcSelector = ref(false);
  const isShowBatchTargetSelector = ref(false);

  const selectedSrcClusters = shallowRef<{
    [key: string]: (SqlServerSingleModel | SqlServerHaModel)[];
  }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  useTicketCloneInfo({
    onSuccess(cloneData) {
      tableData.value = cloneData.infos.map((item) =>
        createRowData({
          clusterData: {
            cloudId: item.src_cluster.bk_cloud_id,
            domain: item.src_cluster.immute_domain,
            id: item.src_cluster.id,
            majorVersion: item.src_cluster.major_version,
          },
          dbIgnoreName: item.ignore_db_list,
          dbName: item.db_list,
          dstClusterData: {
            cloudId: item.dst_cluster.bk_cloud_id,
            domain: item.dst_cluster.immute_domain,
            id: item.dst_cluster.id,
          },
          renameDbName: item.rename_infos,
          restoreBackupFile: item.restore_backup_file,
        }),
      );
    },
    type: TicketTypes.SQLSERVER_ROLLBACK,
  });

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSrcSelector.value = true;
  };

  const handleShowBatchTargetSelector = () => {
    isShowBatchTargetSelector.value = true;
  };

  const handelClusterChange = (selected: { [key: string]: Array<SqlServerSingleModel | SqlServerHaModel> }) => {
    selectedSrcClusters.value = selected;
    const list = _.flatten(Object.values(selected));
    const newList = list.reduce((result, item) => {
      const row = createRowData({
        clusterData: {
          cloudId: item.bk_cloud_id,
          domain: item.master_domain,
          id: item.id,
          majorVersion: item.major_version,
        },
      });
      result.push(row);

      return result;
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
    dataList.splice(index, 1);
    tableData.value = dataList;
  };
  defineExpose<Expose>({
    reset() {
      tableData.value = [createRowData()];
      selectedSrcClusters.value = {
        [ClusterTypes.SQLSERVER_HA]: [],
        [ClusterTypes.SQLSERVER_SINGLE]: [],
      };
      window.changeConfirm = false;
    },
    submit() {
      return Promise.all(rowRefs.value!.map((item) => item.getValue()));
    },
  });
</script>
