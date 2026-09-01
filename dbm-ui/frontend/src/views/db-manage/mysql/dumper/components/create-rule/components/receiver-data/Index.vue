<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
    10| * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="render-data">
    <BkButton @click="handleOpenClusterSelector">
      <DbIcon
        style="margin-right: 8px; color: #979ba5"
        type="add" />
      {{ t('添加数据源集群') }}
    </BkButton>
    <div
      v-if="tableData.length > 0"
      class="mt-16">
      <EditableTable
        ref="tableRef"
        :model="tableData">
        <EditableRow
          v-for="(item, index) in tableData"
          :key="item.rowKey">
          <RenderSourceCluster v-model="item.srcCluster" />
          <EditableColumn
            field="dumperId"
            :label="t('部署dumper实例ID')"
            :min-width="170"
            :rules="requiredRules"
            :width="300">
            <template #headAppend>
              <BatchEditCommon
                :config="batchDialogConfig"
                @data-change="handleBatchInputChange">
                <span
                  v-bk-tooltips="t('批量编辑')"
                  class="batch-edit-btn"
                  @click="() => handleShowBatchEdit('dumperId')">
                  <DbIcon type="bulk-edit" />
                </span>
              </BatchEditCommon>
            </template>
            <EditableInput
              v-model="item.dumperId"
              :placeholder="t('请输入ID')"
              type="number" />
          </EditableColumn>
          <EditableColumn
            :label="t('接收端类型')"
            :min-width="90"
            required
            :rowspan="tableData.length"
            :width="90">
            <EditableSelect
              v-model="receiverType"
              :clearable="false"
              :list="receiverTypeList" />
          </EditableColumn>
          <EditableColumn
            v-if="receiverType !== 'L5_AGENT'"
            field="receiver"
            :label="t('接收端地址')"
            :min-width="120"
            :rules="receiverRules"
            :width="220">
            <template #headAppend>
              <BatchEditCommon
                :config="batchDialogConfig"
                @data-change="handleBatchInputChange">
                <span
                  v-bk-tooltips="t('批量编辑')"
                  class="batch-edit-btn"
                  @click="() => handleShowBatchEdit('receiver')">
                  <DbIcon type="bulk-edit" />
                </span>
              </BatchEditCommon>
            </template>
            <EditableInput
              v-model="item.receiver"
              :placeholder="t('IP_PORT_或_域名_端口')" />
          </EditableColumn>
          <template v-if="receiverType === 'KAFKA'">
            <EditableColumn
              field="account"
              :label="t('账号')"
              :min-width="120"
              :rules="requiredRules"
              :width="220">
              <template #headAppend>
                <BatchEditCommon
                  :config="batchDialogConfig"
                  @data-change="handleBatchInputChange">
                  <span
                    v-bk-tooltips="t('批量编辑')"
                    class="batch-edit-btn"
                    @click="() => handleShowBatchEdit('account')">
                    <DbIcon type="bulk-edit" />
                  </span>
                </BatchEditCommon>
              </template>
              <EditableInput
                v-model="item.account"
                :placeholder="t('请输入账号')" />
            </EditableColumn>
            <EditableColumn
              field="password"
              :label="t('密码')"
              :min-width="120"
              :rules="requiredRules"
              :width="220">
              <template #headAppend>
                <BatchEditCommon
                  :config="batchDialogConfig"
                  @data-change="handleBatchInputChange">
                  <span
                    v-bk-tooltips="t('批量编辑')"
                    class="batch-edit-btn"
                    @click="() => handleShowBatchEdit('password')">
                    <DbIcon type="bulk-edit" />
                  </span>
                </BatchEditCommon>
              </template>
              <EditableInput
                v-model="item.password"
                :placeholder="t('请输入密码')"
                type="password" />
            </EditableColumn>
          </template>
          <template v-if="receiverType === 'L5_AGENT'">
            <EditableColumn
              field="l5ModId"
              label="l5_modid"
              :min-width="120"
              :rules="requiredRules"
              :width="220">
              <template #headAppend>
                <BatchEditCommon
                  :config="batchDialogConfig"
                  @data-change="handleBatchInputChange">
                  <span
                    class="batch-edit-btn"
                    @click="() => handleShowBatchEdit('l5ModId')">
                    <DbIcon type="bulk-edit" />
                  </span>
                </BatchEditCommon>
              </template>
              <EditableInput
                v-model="item.l5ModId"
                :placeholder="t('请输入')"
                type="number" />
            </EditableColumn>
            <EditableColumn
              field="l5CmdId"
              label="l5_cmdid"
              :min-width="120"
              :rules="requiredRules"
              :width="220">
              <template #headAppend>
                <BatchEditCommon
                  :config="batchDialogConfig"
                  @data-change="handleBatchInputChange">
                  <span
                    class="batch-edit-btn"
                    @click="() => handleShowBatchEdit('l5CmdId')">
                    <DbIcon type="bulk-edit" />
                  </span>
                </BatchEditCommon>
              </template>
              <EditableInput
                v-model="item.l5CmdId"
                :placeholder="t('请输入')"
                type="number" />
            </EditableColumn>
          </template>
          <EditableColumn
            fixed="right"
            :label="t('操作')"
            :resizeable="false"
            :width="60">
            <BkButton
              class="delete-column"
              text
              theme="primary"
              @click="handleRemove(index)">
              {{ t('删除') }}
            </BkButton>
          </EditableColumn>
        </EditableRow>
      </EditableTable>
    </div>
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
  import { domainPort } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import BatchEditCommon from './components/batch-edit-common/Index.vue';
  import RenderSourceCluster from './components/RenderSourceCluster.vue';

  interface IDataRow {
    account: string;
    dumperId: string;
    isLoading: boolean;
    l5CmdId: number;
    l5ModId: number;
    password: string;
    receiver: string;
    receiverType: string;
    rowKey: string;
    srcCluster: {
      clusterId: number;
      clusterName: string;
      moduleId: number;
    };
  }

  interface Props {
    selectedClusterList?: TendbhaModel[];
  }

  interface Exposes {
    getTableValue: () => IDataRow[];
    getValue: () => Promise<any[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    selectedClusterList: () => [],
  });

  const { t } = useI18n();

  const tableRef = ref();
  const tableData = ref<IDataRow[]>([]);
  const isShowClusterSelector = ref(false);
  const receiverType = ref('KAFKA');
  const batchDialogConfig = ref({
    key: '',
    placeholder: '',
    title: '',
    type: 'text',
  });

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({ [ClusterTypes.TENDBHA]: [] });

  // 集群域名是否已存在表格的映射表
  const domainMemo: Record<string, boolean> = {};

  const receiverTypeList = [
    {
      label: 'KAFKA',
      value: 'KAFKA',
    },
    {
      label: 'L5_AGENT',
      value: 'L5_AGENT',
    },
    {
      label: 'TCP/IP',
      value: 'TCP/IP',
    },
  ];

  const requiredRules = [
    {
      message: t('不能为空'),
      trigger: 'blur',
      validator: (value: number | string) => Boolean(String(value)),
    },
  ];

  const receiverRules = [
    {
      message: t('不能为空'),
      trigger: 'blur',
      validator: (value: string) => Boolean(value),
    },
    {
      message: t('输入格式有误'),
      trigger: 'blur',
      validator: (value: string) => domainPort.test(value),
    },
  ];

  const batchEditConfigMap = {
    account: {
      placeholder: t('请输入账号'),
      title: t('账号'),
      type: 'text',
    },
    dumperId: {
      placeholder: '',
      title: t('dumper实例ID'),
      type: 'textarea',
    },
    l5CmdId: {
      placeholder: t('请输入'),
      title: 'l5_cmdid',
      type: 'number',
    },
    l5ModId: {
      placeholder: t('请输入'),
      title: 'l5_modid',
      type: 'number',
    },
    password: {
      placeholder: t('请输入密码'),
      title: t('密码'),
      type: 'password',
    },
    receiver: {
      placeholder: t('IP_PORT_或_域名_端口'),
      title: t('接收端地址'),
      type: 'text',
    },
  } as Record<
    string,
    {
      placeholder: string;
      title: string;
      type: string;
    }
  >;

  const generateTableRow = (item: TendbhaModel) => ({
    account: '',
    dumperId: '',
    isLoading: false,
    l5CmdId: 0,
    l5ModId: 0,
    password: '',
    receiver: '',
    receiverType: receiverType.value,
    rowKey: item.master_domain,
    srcCluster: {
      clusterId: item.id,
      clusterName: item.master_domain,
      moduleId: item.db_module_id,
    },
  });

  watch(
    () => props.selectedClusterList,
    (list) => {
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
    },
    {
      immediate: true,
    },
  );

  const handleOpenClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handleBatchInputChange = (data: string[], isBatch: boolean) => {
    if (isBatch) {
      tableData.value.forEach((item, index) => {
        Object.assign(item, {
          dumperId: data[index],
        });
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
    const { placeholder, title, type } = batchEditConfigMap[key];
    batchDialogConfig.value = {
      key,
      placeholder,
      title,
      type,
    };
  };

  // 删除一行
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster.clusterName];
    const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];

    selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter(
      (item) => item.master_domain !== srcCluster.clusterName,
    );
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

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length === 0) {
      return true;
    }
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster.clusterName;
  };

  defineExpose<Exposes>({
    getTableValue: () => tableData.value,
    getValue: () =>
      tableRef.value!.validate().then(() =>
        tableData.value.map((item) => {
          const targetArr = item.receiver ? item.receiver.split(':') : ['', 0];
          const rowObj: Record<string, unknown> = {
            cluster_id: item.srcCluster.clusterId,
            db_module_id: item.srcCluster.moduleId,
            dumper_id: Number(item.dumperId),
            kafka_pwd: item.password, // protocol_type为KAFKA填入用户值
            kafka_user: item.account, // protocol_type为KAFKA填入用户值
            l5_cmdid: Number(item.l5CmdId), // protocol_type为L5_AGENT填入用户值
            l5_modid: Number(item.l5ModId), // protocol_type为L5_AGENT填入用户值
            protocol_type: receiverType.value,
            target_address: targetArr[0], // protocol_type为L5_AGENT要去除
            target_port: Number(targetArr[1]), // protocol_type为L5_AGENT要去除
          };
          if (receiverType.value === 'KAFKA') {
            delete rowObj.l5_modid;
            delete rowObj.l5_cmdid;
          } else if (receiverType.value === 'L5_AGENT') {
            delete rowObj.target_address;
            delete rowObj.target_port;
            delete rowObj.kafka_user;
            delete rowObj.kafka_pwd;
          } else {
            delete rowObj.l5_modid;
            delete rowObj.l5_cmdid;
            delete rowObj.kafka_user;
            delete rowObj.kafka_pwd;
          }
          return rowObj;
        }),
      ),
  });
</script>
<style lang="less">
  .render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }

    .delete-column {
      width: 100%;
    }
  }
</style>
