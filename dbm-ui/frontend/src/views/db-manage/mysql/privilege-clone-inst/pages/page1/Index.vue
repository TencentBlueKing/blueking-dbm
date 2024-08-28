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
    <div class="spider-manage-privilege-clone-inst-page">
      <BkAlert
        closable
        theme="info"
        :title="t('DB 实例权限克隆：DB 实例 IP 替换时，克隆原实例的所有权限到新实例中')" />
      <BkButton
        class="clone-instance-batch mt16"
        @click="() => (isShowBatchInput = true)">
        <i class="db-icon-add" />
        {{ t('批量录入') }}
      </BkButton>
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <TicketRemark v-model="remark" />
      <BatchInput
        v-model:is-show="isShowBatchInput"
        @change="handleBatchInput" />
      <InstanceSelector
        v-model:is-show="isShowBatchInstanceSelector"
        :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
        :selected="selectedIps"
        :tab-list-config="tabListConfig"
        @change="handelInstanceSelectorChange" />
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

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { checkMysqlInstances } from '@services/source/instances';
  import { precheckPermissionClone } from '@services/source/permission';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import BatchInput from './components/BatchInput.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  type InstanceInfo = ServiceReturnType<typeof checkMysqlInstances>[number];

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowBatchInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const isShowBatchInput = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData({})]);
  const remark = ref('');

  const selectedIps = shallowRef<InstanceSelectorValues<TendbhaInstanceModel>>({
    tendbha: [],
    tendbsingle: [],
  });

  let instanceMemo = {} as Record<string, boolean>;

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        tableConfig: {
          firsrColumn: {
            label: '',
            field: '',
            role: '',
          },
        },
        previewConfig: {
          displayKey: 'instance_address',
          showTitle: true,
          title: t('主从'),
        },
      },
    ],
    [ClusterTypes.TENDBSINGLE]: [
      {
        previewConfig: {
          displayKey: 'instance_address',
          showTitle: true,
          title: t('单节点'),
        },
      },
      {
        manualConfig: {
          activePanelId: 'manualInput',
        },
        previewConfig: {
          showTitle: true,
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.source && !firstRow.target;
  };

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<{ source: string; target: string }>) {
    const instanceListInfos = await checkMysqlInstances({
      bizId: currentBizId,
      instance_addresses: _.flatMap(list.map((item) => [item.source, item.target])),
    });
    const instanceInfoMap = instanceListInfos.reduce<Record<string, InstanceInfo>>(
      (results, item) =>
        Object.assign(results, {
          [item.instance_address]: item,
        }),
      {},
    );
    const formatList = list.map((item) => {
      const sourceInstance = instanceInfoMap[item.source];
      const targetInstance = instanceInfoMap[item.target];
      return {
        ...createRowData(),
        source: {
          bkCloudId: sourceInstance.bk_cloud_id,
          clusterId: sourceInstance.cluster_id,
          dbModuleId: sourceInstance.db_module_id,
          dbModuleName: sourceInstance.db_module_name,
          instanceAddress: sourceInstance.instance_address,
          masterDomain: sourceInstance.master_domain,
          clusterType: sourceInstance.cluster_type,
        },
        target: {
          cluster_id: targetInstance.cluster_id,
          bk_host_id: targetInstance.bk_host_id,
          bk_cloud_id: targetInstance.bk_cloud_id,
          port: targetInstance.port,
          ip: targetInstance.ip,
          instance_address: targetInstance.instance_address,
        },
      };
    });

    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  }

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchInstanceSelector.value = true;
  };
  // 批量选择
  const handelInstanceSelectorChange = (data: InstanceSelectorValues<TendbhaInstanceModel>) => {
    selectedIps.value = data;
    const dataList = Object.values(data).reduce((list, items) => list.concat(items));
    const newList = dataList.reduce<IDataRow[]>((results, item) => {
      const { instance_address: ip } = item;
      if (!instanceMemo[ip]) {
        const row = createRowData({
          source: {
            clusterId: item.cluster_id,
            clusterType: item.cluster_type,
            masterDomain: item.master_domain,
            dbModuleId: item.db_module_id,
            dbModuleName: item.db_module_name,
            instanceAddress: item.instance_address,
            bkCloudId: item.bk_cloud_id,
          },
        });
        results.push(row);
        instanceMemo[ip] = true;
      }
      return results;
    }, []);
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
    const { instanceAddress, clusterType } = dataList[index].source!;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (instanceAddress) {
      delete instanceMemo[instanceAddress];
      const clustersArr = selectedIps.value[clusterType];
      selectedIps.value[clusterType] = clustersArr.filter((item) => item.instance_address !== instanceAddress);
    }
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, sourceData);
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) =>
        precheckPermissionClone({
          bizId: currentBizId,
          clone_type: 'instance',
          clone_list: data,
          clone_cluster_type: 'mysql',
        }).then((precheckResult) => {
          if (!precheckResult.pre_check) {
            return Promise.reject();
          }

          const params = {
            ticket_type: TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
            remark: remark.value,
            details: {
              ...precheckResult,
              clone_type: 'instance',
            },
            bk_biz_id: currentBizId,
          };
          return createTicket(params).then((data) => {
            window.changeConfirm = false;

            router.push({
              name: 'MySQLPrivilegeCloneInst',
              params: {
                page: 'success',
              },
              query: {
                ticketId: data.id,
              },
            });
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = '';
    instanceMemo = {};
    selectedIps.value.tendbha = [];
    selectedIps.value.tendbsingle = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .spider-manage-privilege-clone-inst-page {
    padding-bottom: 20px;
  }
</style>
