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
  <div class="render-data">
    <BkButton
      class="mb-16"
      @click="handleOpenClusterSelector">
      <DbIcon
        style="margin-right: 8px;color: #979BA5"
        type="add" />
      {{ t('添加数据源集群') }}
    </BkButton>
    <RenderTable>
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :width="220">
          <span>{{ t('数据源集群') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="170"
          :required="false"
          :width="300">
          <template #append>
            <span
              class="batch-edit-btn"
              @click="() => handleShowBatchEdit('dumperId')">
              <DbIcon type="bulk-edit" />
            </span>
          </template>
          <span>{{ t('部署dumper实例ID') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="90"
          :width="90">
          <span>{{ t('接收端类型') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          v-if="receiverType !== 'L5_AGENT'"
          :min-width="120"
          :required="false"
          :width="220">
          <template #append>
            <span
              class="batch-edit-btn"
              @click="() => handleShowBatchEdit('receiver')">
              <DbIcon type="bulk-edit" />
            </span>
          </template>
          <span>{{ t('接收端地址') }}</span>
        </RenderTableHeadColumn>
        <template v-if="receiverType === 'KAFKA'">
          <RenderTableHeadColumn
            :min-width="120"
            :required="false"
            :width="220">
            <template #append>
              <span
                class="batch-edit-btn"
                @click="() => handleShowBatchEdit('account')">
                <DbIcon type="bulk-edit" />
              </span>
            </template>
            <span>{{ t('账号') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :min-width="120"
            :required="false"
            :width="220">
            <template #append>
              <span
                class="batch-edit-btn"
                @click="() => handleShowBatchEdit('password')">
                <DbIcon type="bulk-edit" />
              </span>
            </template>
            <span>{{ t('密码') }}</span>
          </RenderTableHeadColumn>
        </template>
        <template v-if="receiverType === 'L5_AGENT'">
          <RenderTableHeadColumn
            :min-width="120"
            :required="false"
            :width="220">
            <template #append>
              <span
                class="batch-edit-btn"
                @click="() => handleShowBatchEdit('l5ModId')">
                <DbIcon type="bulk-edit" />
              </span>
            </template>
            <span>l5_modid</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :min-width="120"
            :required="false"
            :width="220">
            <template #append>
              <span
                class="batch-edit-btn"
                @click="() => handleShowBatchEdit('l5CmdId')">
                <DbIcon type="bulk-edit" />
              </span>
            </template>
            <span>l5_cmdid</span>
          </RenderTableHeadColumn>
        </template>
        <RenderTableHeadColumn
          fixed="right"
          :required="false"
          :width="60">
          {{ t('操作') }}
        </RenderTableHeadColumn>
      </template>
      <template #data>
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :index="index"
          :removeable="tableData.length < 2"
          :row-span="tableData.length"
          :type="receiverType"
          @cluster-input-finish="(value: IDataRow['srcCluster']) => handleClusterInputFinish(index, value)"
          @remove="handleRemove(index)"
          @type-change="handleReceiverTypeChange" />
      </template>
    </RenderTable>
    <BatchEditCommon
      v-model="isShowBatchEdit"
      :config="batchDialogConfig"
      @data-change="handleBatchInputChange" />
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.TENDBHA]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import BatchEditCommon from './components/batch-edit-common/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface Props {
    selectedClusterList?: TendbhaModel[];
  }

  interface Exposes {
    getValue: () => Promise<any[]>,
  }

  const props = withDefaults(defineProps<Props>(), {
    selectedClusterList: () => ([]),
  });

  const { t } = useI18n();

  const tableData = ref([createRowData()]);
  const rowRefs = ref();
  const isShowClusterSelector = ref(false);
  const isShowBatchEdit = ref(false);
  const receiverType = ref('KAFKA');
  const batchDialogConfig = ref({
    type: 'text',
    key: '',
    title: '',
    placeholder: '',
  });

  const selectedClusters = shallowRef<{[key: string]: Array<TendbhaModel>}>({ [ClusterTypes.TENDBCLUSTER]: [] });

  // 集群域名是否已存在表格的映射表
  const domainMemo:Record<string, boolean> = {};

  const batchEditConfigMap = {
    dumperId: {
      type: 'textarea',
      title: t('dumper实例ID'),
      placeholder: '',
    },
    receiver: {
      type: 'text',
      title: t('接收端地址'),
      placeholder: t('IP_PORT_或_域名_端口'),
    },
    account: {
      type: 'text',
      title: t('账号'),
      placeholder: t('请输入账号'),
    },
    password: {
      type: 'password',
      title: t('密码'),
      placeholder: t('请输入密码'),
    },
    l5ModId: {
      type: 'number',
      title: 'l5_modid',
      placeholder: t('请输入'),
    },
    l5CmdId: {
      type: 'number',
      title: 'l5_cmdid',
      placeholder: t('请输入'),
    },
  } as Record<string, {
    type: string,
    title: string,
    placeholder: string,
  }>;

  const generateTableRow = (item: TendbhaModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    srcCluster: {
      clusterName: item.master_domain,
      clusterId: item.id,
      moduleId: item.db_module_id,
    },
    dumperId: '',
    receiver: '',
    receiverType: receiverType.value,
    account: '',
    password: '',
    l5ModId: 0,
    l5CmdId: 0,
  });

  watch(() => props.selectedClusterList, (list) => {
    if (list.length > 0) {
      const newList: IDataRow[] = [];
      list.forEach((item) => {
        const domain = item.master_domain;
        if (!domainMemo[domain]) {
          const row = generateTableRow(item);
          newList.push(row);
          domainMemo[domain] = true;
        }
      });
      tableData.value = newList;
    }
  }, {
    immediate: true,
  });

  const handleOpenClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handleBatchInputChange = (data: string[], isBatch: boolean) => {
    if (isBatch) {
      data.forEach((id, index) => {
        const tableLen = tableData.value.length;
        if (index <= tableLen - 1) {
          tableData.value[index].dumperId = id;
        } else {
          const obj = createRowData();
          obj.dumperId = id;
          tableData.value.push(obj);
        }
      });
      return;
    }
    const [value] = data;
    const { key } = batchDialogConfig.value;
    tableData.value.forEach((item) => {
      Object.assign(item, {
        [key]: value,
      });
    });
  };

  const handleShowBatchEdit = (key: string) => {
    const { type, title, placeholder } = batchEditConfigMap[key];
    batchDialogConfig.value = {
      type,
      key,
      title,
      placeholder,
    };
    isShowBatchEdit.value = true;
  };

  const handleReceiverTypeChange = (type: string) => {
    receiverType.value = type;
  };

  // 删除一行
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster.clusterName];
    const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
    // eslint-disable-next-line max-len
    selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter(item => item.cluster_name !== srcCluster.clusterName);
  };

  // 批量选择
  const handelClusterChange = async (selected: Record<string, TendbhaModel[]>) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.TENDBHA];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateTableRow(item);
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  const handleClusterInputFinish = (index: number, obj: IDataRow['srcCluster']) => {
    tableData.value[index].srcCluster = obj;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster.clusterName;
  };

  defineExpose<Exposes>({
    getValue: () => Promise.all(rowRefs.value.map((item: {
      getValue: () => Promise<any>
    }) => item.getValue())),
  });
</script>
<style lang="less">
.render-data {
  .batch-edit-btn {
    margin-left: 4px;
    color: #3a84ff;
    cursor: pointer;
  }
}

</style>
