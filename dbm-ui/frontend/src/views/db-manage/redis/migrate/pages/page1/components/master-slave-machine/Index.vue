<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <div class="render-data mb-24">
      <RenderTable>
        <template #default>
          <RenderTableHeadColumn
            fixed="left"
            :width="200">
            <span>{{ t('目标 Master 主机') }}</span>
            <template #append>
              <BatchOperateIcon
                class="ml-4"
                @click="handleShowMasterBatchSelector" />
            </template>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :required="false"
            :width="100">
            <span>{{ t('关联的主从实例') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn :width="220">
            <span>{{ t('规格') }}</span>
            <template #append>
              <BatchEditColumn
                v-model="batchEditShow.targetSpecId"
                :data-list="specList"
                :title="t('规格')"
                @change="(value: string | string[]) => handleBatchEditChange(value, 'targetSpecId')">
                <BatchOperateIcon
                  class="ml-4"
                  type="edit"
                  @click="handleShowBatchEdit('targetSpecId')" />
              </BatchEditColumn>
            </template>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn :width="220">
            <span>{{ t('版本') }}</span>
            <template #append>
              <BatchEditColumn
                v-model="batchEditShow.targetVersion"
                :data-list="versionList"
                :title="t('版本')"
                @change="(value: string | string[]) => handleBatchEditChange(value, 'targetVersion')">
                <BatchOperateIcon
                  class="ml-4"
                  type="edit"
                  @click="handleShowBatchEdit('targetVersion')" />
              </BatchEditColumn>
            </template>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            fixed="right"
            :required="false"
            :width="100">
            {{ t('操作') }}
          </RenderTableHeadColumn>
        </template>
        <template #data>
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :removeable="tableData.length < 2"
            @add="(payload) => handleAppend(index, payload)"
            @clone="(payload) => handleClone(index, payload)"
            @ip-input-finish="(ip) => handleChangeCluster(index, ip)"
            @remove="handleRemove(index)" />
        </template>
      </RenderTable>
      <TicketRemark v-model="localRemark" />
      <InstanceSelector
        v-model:is-show="isShowClusterSelector"
        :cluster-types="['RedisHost']"
        :selected="selectedClusters"
        :tab-list-config="tabListConfig"
        @change="handelClusterChange" />
    </div>
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
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import RedisMachineModel from '@services/model/redis/redis-machine';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { listPackages } from '@services/source/package';
  import { getRedisMachineList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import InstanceSelector, { type PanelListType } from '@components/instance-selector/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';
  import BatchOperateIcon from '@views/db-manage/common/batch-operate-icon/Index.vue';
  import { QueryKeyMap, specClusterMachineMap } from '@views/db-manage/redis/common/const';

  import { random } from '@utils';

  import RenderDataRow, { createRowData, type IDataRow, type IDataRowBatchKey } from './Row.vue';

  interface Props {
    tableList: IDataRow[];
    remark: string;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>();
  const isSubmitting = ref(false);
  const localRemark = ref('');

  const batchEditShow = reactive({
    targetSpecId: false,
    targetVersion: false,
  });

  const tabListConfig = {
    RedisHost: [
      {
        topoConfig: {
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.redis_master.forEach((masterItem) => ipSet.add(masterItem.ip)));
            return ipSet.size;
          },
        },
        tableConfig: {
          getTableList: (params: ServiceReturnType<typeof getRedisMachineList>) =>
            getRedisMachineList({
              cluster_type: ClusterTypes.REDIS_INSTANCE,
              ...params,
            }),
          disabledRowConfig: {
            handler: (data: RedisMachineModel) =>
              data.isUnvailable || data.related_instances.some((item) => item.status === 'unavailable'),
            tip: t('集群或实例状态异常，不可选择'),
          },
        },
      },
      {
        manualConfig: {
          checkInstances: (params: ServiceReturnType<typeof getRedisMachineList>) =>
            getRedisMachineList({
              cluster_type: ClusterTypes.REDIS_INSTANCE,
              ...params,
            }),
        },
        tableConfig: {
          disabledRowConfig: {
            handler: (data: RedisMachineModel) =>
              data.isUnvailable || data.related_instances.some((item) => item.status === 'unavailable'),
            tip: t('集群或实例状态异常，不可选择'),
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const selectedClusters = shallowRef<{ [key: string]: RedisMachineModel[] }>({ ['RedisHost']: [] });

  const specList = shallowRef<
    {
      value: number;
      label: string;
    }[]
  >();
  const versionList = shallowRef<
    {
      value: string;
      label: string;
    }[]
  >([]);

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: ClusterTypes.REDIS,
        spec_machine_type: specClusterMachineMap[ClusterTypes.REDIS_INSTANCE],
        limit: -1,
        offset: 0,
      },
    ],
    onSuccess(listResult) {
      specList.value = listResult.results.map((item) => ({
        value: item.spec_id,
        label: item.spec_name,
      }));
    },
  });

  useRequest(listPackages, {
    defaultParams: [
      {
        db_type: DBTypes.REDIS,
        query_key: QueryKeyMap[ClusterTypes.REDIS_INSTANCE],
      },
    ],
    onSuccess(listResult) {
      versionList.value = listResult.map((item) => ({
        value: item,
        label: item,
      }));
    },
  });

  watchEffect(() => {
    tableData.value = props.tableList.length > 0 ? props.tableList : [createRowData()];
  });

  watchEffect(() => {
    localRemark.value = props.remark;
  });

  // master主机是否已存在表格的映射表
  let ipMemo: Record<string, boolean> = {};

  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: IDataRow[]) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    if (removeItem.clusterData) {
      const { ip } = removeItem.clusterData;
      delete ipMemo[ip];
      const hostList = selectedClusters.value.RedisHost;
      selectedClusters.value.RedisHost = hostList.filter((item) => item.ip !== ip);
    }
    tableData.value.splice(index, 1);
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    tableData.value.splice(index + 1, 0, sourceData);
    setTimeout(() => {
      rowRefs.value![rowRefs.value!.length - 1].getValue();
    });
  };

  const generateTableRow = (item: RedisMachineModel) => ({
    rowKey: random(),
    isLoading: false,
    clusterData: {
      ip: item.ip,
      cloudId: item.bk_cloud_id,
      clusterType: ClusterTypes.REDIS_INSTANCE,
      // related_cluster: item.related_clusters,
      relatedInstance: item.related_instances,
      currentSpecId: item.spec_config.id,
      dbVersion: item.related_clusters[0].major_version,
    },
  });

  // 批量选择
  const handelClusterChange = async (selected: Record<string, RedisMachineModel[]>) => {
    selectedClusters.value = selected;
    const machineList = selected.RedisHost;
    const newList: IDataRow[] = [];
    machineList.forEach((item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        newList.push(generateTableRow(item));
        ipMemo[ip] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, ip: string) => {
    tableData.value[index].isLoading = true;
    const result = await getRedisMachineList({ ip }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length > 0) {
      const machineItem = result.results[0];
      const row = generateTableRow(machineItem);
      tableData.value[index] = row;
      ipMemo[machineItem.ip] = true;
      selectedClusters.value.RedisHost.push(machineItem);
    }
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  const handleShowBatchEdit = (col: keyof typeof batchEditShow) => {
    batchEditShow[col] = !batchEditShow[col];
  };

  const handleBatchEditChange = (value: string | string[], filed: IDataRowBatchKey) => {
    if (!value || checkListEmpty(tableData.value)) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, {
        [filed]: value,
      });
    });
  };

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const rowInfos = await Promise.all(rowRefs.value!.map((item) => item.getValue()));
      const infos = rowInfos
        .map((infoItem) =>
          infoItem.instance.map((instaneItem) => ({
            ...instaneItem,
            resource_spec: infoItem.resource_spec,
            db_version: infoItem.db_version,
            display_info: infoItem.display_info,
          })),
        )
        .flat();
      await createTicket({
        ticket_type: TicketTypes.REDIS_SINGLE_INS_MIGRATE,
        remark: localRemark.value,
        details: {
          infos,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'RedisMigrate',
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
    localRemark.value = '';
    ipMemo = {};
    selectedClusters.value.RedisHost = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .render-data {
    .storage-remote-form {
      :deep(.bk-form-label) {
        font-size: 12px;
        font-weight: 700;
        color: #313238;
      }
    }
  }
</style>
