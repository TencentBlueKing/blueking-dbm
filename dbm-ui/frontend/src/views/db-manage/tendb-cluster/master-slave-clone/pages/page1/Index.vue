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
    <div class="spider-master-slave-clone">
      <BkAlert
        closable
        theme="info"
        :title="t('迁移主从：主从机器上的所有实例成对迁移到新机器上，旧机器会下架掉。')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @host-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
          @remove="handleRemove(index)" />
      </RenderData>
      <BkForm
        class="toolbox-form mt-24"
        form-type="vertical">
        <BkFormItem
          :label="t('备份源')"
          required>
          <BkRadioGroup v-model="formData.backup_source">
            <BkRadio label="local">
              {{ t('本地备份') }}
            </BkRadio>
            <BkRadio label="remote">
              {{ t('远程备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
      <TicketRemark v-model="formData.remark" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="totalNum === 0"
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <InstanceSelector
      v-model:is-show="isShowMasterInstanceSelector"
      :cluster-types="['TendbClusterHost']"
      :selected="selected"
      @change="handleInstanceSelectChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getTendbclusterMachineList } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import { random } from '@utils';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/Row.vue';

  const createDefaultData = () => ({
    backup_source: 'local',
    remark: '',
  });

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER,
    onSuccess(cloneData) {
      const { tableDataList, remark, backupSource } = cloneData;
      tableData.value = tableDataList;
      formData.backup_source = backupSource;
      formData.remark = remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref([createRowData()]);

  const formData = reactive(createDefaultData());

  const selected = shallowRef({ TendbClusterHost: [] } as InstanceSelectorValues<IValue>);

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.clusterData.ip)).length);

  // ip 是否已存在表格的映射表
  let ipMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length === 0) {
      return true;
    }
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData.ip;
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  const generateRowDateFromRequest = (item: IValue) => ({
    rowKey: random(),
    isLoading: false,
    clusterData: {
      ip: item.ip,
      clusterId: item.cluster_id,
      domain: item.master_domain || '',
      cloudId: item.bk_cloud_id,
      cloudName: item.bk_cloud_name || '',
      hostId: item.bk_host_id,
    },
    masterInstanceList: item.related_instances || [],
    newHostList: [],
  });

  // 批量选择
  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    selected.value = data;
    const newList: IDataRow[] = [];
    data.TendbClusterHost.forEach((item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        newList.push(generateRowDateFromRequest(item));
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

  // 输入IP后查询详细信息
  const handleChangeHostIp = async (index: number, ip: string) => {
    if (!ip) {
      const { ip } = tableData.value[index].clusterData;
      ipMemo[ip] = false;
      Object.assign(tableData.value[index].clusterData, {
        id: 0,
        ip: '',
        clusterId: 0,
        domain: '',
        cloudId: 0,
        cloudName: '',
      });
      return;
    }
    tableData.value[index].isLoading = true;
    const spiderMachineResult = await getTendbclusterMachineList({
      ip,
      instance_role: 'remote_master',
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (spiderMachineResult.results.length === 0) {
      return;
    }
    const spiderMachineItem = spiderMachineResult.results[0];
    Object.assign(tableData.value[index], {
      clusterData: {
        ip,
        clusterId: spiderMachineItem.related_clusters[0].id,
        domain: spiderMachineItem.related_clusters[0].immute_domain,
        cloudId: spiderMachineItem.bk_cloud_id,
        cloudName: spiderMachineItem.bk_cloud_name,
      },
      masterInstanceList: spiderMachineItem.related_instances,
    });
    ipMemo[ip] = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const removeIp = removeItem.clusterData.ip;
    tableData.value.splice(index, 1);
    delete ipMemo[removeIp];
    const ipsArr = selected.value.TendbClusterHost;
    selected.value.TendbClusterHost = ipsArr.filter((item) => item.ip !== removeIp);
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    const rowData = _.cloneDeep(dataList[index]);
    dataList.splice(
      index + 1,
      0,
      Object.assign(sourceData, {
        clusterData: {
          ...sourceData.clusterData,
          domain: tableData.value[index].clusterData?.domain ?? '',
        },
        masterInstanceList: rowData.masterInstanceList,
      }),
    );
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value![rowRefs.value!.length - 1].getValue();
    });
  };

  // 提交
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const rowDataList = await Promise.all(rowRefs.value!.map((item) => item.getValue()));
      const params = {
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER,
        remark: formData.remark,
        details: {
          ...formData,
          ip_source: 'manual_input',
          infos: rowDataList.map((rowItem, rowIndex) => {
            const { clusterData } = tableData.value[rowIndex];
            return {
              cluster_id: clusterData.clusterId,
              new_master: rowItem.newInstaceList[0],
              new_slave: rowItem.newInstaceList[1],
              old_master: {
                ip: clusterData.ip,
                bk_cloud_id: clusterData.cloudId,
                bk_host_id: clusterData.hostId,
                bk_biz_id: currentBizId,
              },
              old_slave: rowItem.old_master,
            };
          }),
        },
      };

      await createTicket(params).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'spiderMasterSlaveClone',
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

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultData());
    tableData.value = [createRowData()];
    selected.value.TendbClusterHost = [];
    ipMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .spider-master-slave-clone {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
