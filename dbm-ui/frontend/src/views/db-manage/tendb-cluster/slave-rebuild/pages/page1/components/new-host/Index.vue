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
    <div class="spider-slave-rebuild-original-host-box">
      <RenderData
        class="mt16"
        @show-ip-selector="handleShowIpSelector">
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <InstanceSelector
      v-model:is-show="isShowInstanceSelecotr"
      :cluster-types="['TendbClusterHost']"
      :selected="selected"
      :tab-list-config="tabListConfig"
      @change="handleInstancesChange" />
  </SmartAction>
</template>

<script lang="tsx">
  export const createDefaultFormData = () => ({
    backup_source: 'local',
    remark: '',
  });
</script>
<script setup lang="tsx">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getTendbclusterMachineList } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import { random } from '@utils';

  import RenderData from './components/render-data/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/render-data/Row.vue';

  interface Props {
    ticketCloneData?: {
      tableDataList: IDataRow[];
      formData: UnwrapRef<typeof formData>;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const isShowInstanceSelecotr = ref(false);
  const rowRefs = ref([] as InstanceType<typeof RenderDataRow>[]);
  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const selected = shallowRef({ TendbClusterHost: [] } as InstanceSelectorValues<IValue>);

  const tabListConfig = {
    TendbClusterHost: [
      {
        name: t('目标从库'),
        tableConfig: {
          firsrColumn: {
            label: t('Slave 主机'),
            field: 'ip',
            role: 'remote_slave',
          },
        },
      },
      {
        tableConfig: {
          firsrColumn: {
            label: t('Slave 主机'),
            field: 'ip',
            role: 'remote_slave',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  let ipMemo = {} as Record<string, boolean>;

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.oldSlave?.ip)).length);

  watch(
    () => props.ticketCloneData,
    () => {
      if (props.ticketCloneData) {
        tableData.value = props.ticketCloneData.tableDataList;
        Object.assign(formData, props.ticketCloneData.formData);
      }
    },
  );

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.oldSlave || !firstRow.oldSlave.ip;
  };

  const handleShowIpSelector = () => {
    isShowInstanceSelecotr.value = true;
  };

  const generateRowDateFromRequest = (item: IValue) => ({
    rowKey: random(),
    isLoading: false,
    oldSlave: {
      bkCloudId: item.bk_cloud_id,
      bkCloudName: item.bk_cloud_name || '',
      bkHostId: item.bk_host_id,
      ip: item.ip,
      domian: item.master_domain || '',
      clusterId: item.cluster_id,
      specConfig: item.spec_config || ({} as IDataRow['oldSlave']['specConfig']),
      slaveInstanceList: item.related_instances || ([] as IDataRow['oldSlave']['slaveInstanceList']),
    },
  });

  const handleInstancesChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    selected.value = selectedValues;
    const newList: IDataRow[] = [];
    selectedValues.TendbClusterHost.forEach((instanceData) => {
      const { ip } = instanceData;
      if (!ipMemo[ip]) {
        newList.push(generateRowDateFromRequest(instanceData));
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
      const { ip } = tableData.value[index].oldSlave;
      ipMemo[ip] = false;
      tableData.value[index] = createRowData();
      return;
    }
    tableData.value[index].isLoading = true;
    const spiderMachineResult = await getTendbclusterMachineList({
      ip,
      instance_role: 'remote_slave',
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (spiderMachineResult.results.length === 0) {
      return;
    }
    const spiderMachineItem = spiderMachineResult.results[0];
    Object.assign(tableData.value[index].oldSlave, {
      bkCloudId: spiderMachineItem.bk_cloud_id,
      bkCloudName: spiderMachineItem.bk_cloud_name,
      bkHostId: spiderMachineItem.bk_host_id,
      ip: spiderMachineItem.ip,
      clusterId: spiderMachineItem.related_clusters[0].id,
      domian: spiderMachineItem.related_clusters[0].immute_domain,
      specConfig: spiderMachineItem.spec_config,
      slaveInstanceList: spiderMachineItem.related_instances.map((instanceItem) => ({
        status: instanceItem.status,
        instance: instanceItem.instance,
      })),
    });
    ipMemo[ip] = true;
  };

  // 追加一个行
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个行
  const handleRemove = (index: number) => {
    const ip = tableData.value[index].oldSlave?.ip;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selected.value.TendbClusterHost;
      selected.value.TendbClusterHost = clustersArr.filter((item) => item.ip !== ip);
    }
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
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

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(rowRefs.value.map((item) => item.getValue()));
      await createTicket({
        ticket_type: TicketTypes.TENDBCLUSTER_RESTORE_SLAVE,
        remark: '',
        details: {
          ip_source: 'resource_pool',
          backup_source: formData.backup_source,
          infos,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'spiderSlaveRebuild',
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
    Object.assign(formData, createDefaultFormData());
    tableData.value = [createRowData()];
    ipMemo = {};
    selected.value.TendbClusterHost = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .spider-slave-rebuild-original-host-box {
    padding-bottom: 20px;

    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }

    .item-block {
      margin-top: 24px;
    }
  }
</style>
