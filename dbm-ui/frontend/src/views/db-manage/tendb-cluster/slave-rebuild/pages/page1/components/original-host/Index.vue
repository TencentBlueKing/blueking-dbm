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
      :cluster-types="[ClusterTypes.TENDBCLUSTER]"
      :selected="selectedIntances"
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
  import { ref, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { checkMysqlInstances } from '@services/source/instances';
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

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

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

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: [
      {
        name: t('目标从库'),
        tableConfig: {
          firsrColumn: {
            label: t('Slave 实例'),
            field: 'instance_address',
            role: 'remote_slave',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  let instanceMemo = {} as Record<string, boolean>;

  const isShowInstanceSelecotr = ref(false);
  const rowRefs = ref([] as InstanceType<typeof RenderDataRow>[]);
  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const selectedIntances = shallowRef<InstanceSelectorValues<IValue>>({ [ClusterTypes.TENDBCLUSTER]: [] });

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.slave)).length);

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
    return !firstRow.slave || !firstRow.slave.instanceAddress;
  };

  const handleShowIpSelector = () => {
    isShowInstanceSelecotr.value = true;
  };

  const generateRowDateFromRequest = (item: IValue) => ({
    rowKey: random(),
    isLoading: false,
    slave: {
      bkCloudId: item.bk_cloud_id,
      bkHostId: item.bk_host_id,
      ip: item.ip,
      port: item.port,
      instanceAddress: item.instance_address,
      clusterId: item.cluster_id,
      domain: item.master_domain || '',
    },
  });

  const handleInstancesChange = (selected: InstanceSelectorValues<IValue>) => {
    selectedIntances.value = selected;
    const newList: IDataRow[] = [];
    selected[ClusterTypes.TENDBCLUSTER].forEach((instanceData) => {
      const { instance_address: instance } = instanceData;
      if (!instanceMemo[instance]) {
        newList.push(generateRowDateFromRequest(instanceData));
        instanceMemo[instance] = true;
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
  const handleChangeHostIp = async (index: number, value: string) => {
    if (!value) {
      const { ip, port } = tableData.value[index].slave!;
      instanceMemo[`${ip}${port}`] = false;
      tableData.value[index] = createRowData();
      return;
    }
    tableData.value[index].isLoading = true;
    const instanceList = await checkMysqlInstances({
      bizId: currentBizId,
      instance_addresses: [value],
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (instanceList.length === 0) {
      return;
    }
    const instaneItem = instanceList[0];
    Object.assign(tableData.value[index].slave, {
      bkCloudId: instaneItem.bk_cloud_id,
      bkHostId: instaneItem.bk_host_id,
      ip: instaneItem.ip,
      port: instaneItem.port,
      instanceAddress: instaneItem.instance_address,
      clusterId: instaneItem.cluster_id,
      domain: instaneItem.master_domain,
    });
    instanceMemo[value] = true;
  };

  // 追加一个行
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个行
  const handleRemove = (index: number) => {
    const instanceAddress = tableData.value[index].slave?.instanceAddress;
    if (instanceAddress) {
      delete instanceMemo[instanceAddress];
      const clustersArr = selectedIntances.value[ClusterTypes.TENDBCLUSTER];
      selectedIntances.value[ClusterTypes.TENDBCLUSTER] = clustersArr.filter(
        (item) => item.instance_address !== instanceAddress,
      );
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
      await Promise.all(rowRefs.value.map((item) => item.getValue()));
      await createTicket({
        ticket_type: TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
        remark: formData.remark,
        details: {
          backup_source: formData.backup_source,
          infos: tableData.value.map((tableItem) => {
            const { slave } = tableItem;
            return {
              cluster_id: slave.clusterId,
              slave: {
                bk_biz_id: currentBizId,
                bk_cloud_id: slave.bkCloudId,
                bk_host_id: slave.bkHostId,
                ip: slave.ip,
                port: slave.port,
              },
            };
          }),
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
    instanceMemo = {};
    selectedIntances.value[ClusterTypes.TENDBCLUSTER] = [];
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
