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
    <div class="mysql-slave-rebuild-original-host-box">
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
          @remove="handleRemove(index)" />
      </RenderData>
      <BkForm
        class="mt-24"
        form-type="vertical">
        <BkFormItem
          :label="t('备份源')"
          required>
          <BkRadioGroup v-model="backupSource">
            <BkRadio label="local">
              {{ t('本地备份') }}
            </BkRadio>
            <BkRadio label="remote">
              {{ t('远程备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
      :cluster-types="[ClusterTypes.TENDBHA]"
      :selected="selectedIps"
      :tab-list-config="tabListConfig"
      @change="handleInstancesChange" />
  </SmartAction>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

<<<<<<< HEAD
  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
=======
  import InstanceSelector, { type InstanceSelectorValues } from '@components/instance-selector/Index.vue';
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const isShowInstanceSelecotr = ref(false);
  const rowRefs = ref([] as InstanceType<typeof RenderDataRow>[]);
  const backupSource = ref('local');
  const isSubmitting = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIps = shallowRef<InstanceSelectorValues<TendbhaInstanceModel>>({ [ClusterTypes.TENDBHA]: [] });

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        name: t('待重建从库主机'),
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  let ipMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.oldSlave;
  };

  // Master 批量选择
  const handleShowIpSelector = () => {
    isShowInstanceSelecotr.value = true;
  };

<<<<<<< HEAD
  const handleInstancesChange = (selected: InstanceSelectorValues<TendbhaInstanceModel>) => {
    selectedIps.value = selected;
    const newList: IDataRow[] = [];
    selected[ClusterTypes.TENDBHA].forEach((instanceData) => {
      const { ip } = instanceData;
      if (!ipMemo[ip]) {
        const row = createRowData({
          oldSlave: {
            bkCloudId: instanceData.bk_cloud_id,
            bkCloudName: instanceData.bk_cloud_name,
            bkHostId: instanceData.bk_host_id,
            ip,
            port: instanceData.port,
            instanceAddress: instanceData.instance_address,
            clusterId: instanceData.cluster_id,
          },
        });
        newList.push(row);
        ipMemo[ip] = true;
      }
    });
=======
  const handleInstancesChange = (selected: InstanceSelectorValues) => {
    const newList = selected[ClusterTypes.TENDBHA].map((instanceData) =>
      createRowData({
        oldSlave: {
          bkCloudId: instanceData.bk_cloud_id,
          bkCloudName: instanceData.bk_cloud_name,
          bkHostId: instanceData.bk_host_id,
          ip: instanceData.ip,
          port: instanceData.port,
          instanceAddress: instanceData.instance_address,
          clusterId: instanceData.cluster_id,
        },
      }),
    );
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)

    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
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
      const clustersArr = selectedIps.value[ClusterTypes.TENDBHA];
      selectedIps.value[ClusterTypes.TENDBHA] = clustersArr.filter(item => item.ip !== ip);
    }
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item) => item.getValue()))
      .then((data) =>
        createTicket({
          ticket_type: 'MYSQL_RESTORE_SLAVE',
          remark: '',
          details: {
            backup_source: backupSource.value,
            infos: data,
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;

          router.push({
            name: 'MySQLSlaveRebuild',
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
    ipMemo = {};
    selectedIps.value[ClusterTypes.TENDBHA] = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mysql-slave-rebuild-original-host-box {
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
