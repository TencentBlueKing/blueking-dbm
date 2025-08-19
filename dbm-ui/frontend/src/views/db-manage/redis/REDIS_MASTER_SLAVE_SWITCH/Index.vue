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
    <div class="redis-master-failover-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t(
            '主从切换：针对TendisSSD、TendisCache，主从切换是把Slave提升为Master，原Master被剔除，针对Tendisplus集群，主从切换是把Slave和Master互换',
          )
        " />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <HostColumn
              v-model="item.host"
              :cluster-types="[ClusterTypes.REDIS]"
              :label="t('主库主机')"
              :placeholder="t('请输入IP（单个）')"
              :selected="selected"
              @batch-edit="handleHostBatchEdit" />
            <EditableColumn
              :label="t('所属集群')"
              :min-width="300">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                <div
                  v-for="(relatedClusterItem, relatedClusterIndex) in item.host.related_clusters"
                  :key="relatedClusterIndex">
                  {{ relatedClusterItem.immute_domain }}
                </div>
              </EditableBlock>
            </EditableColumn>
            <MasterSlaveInfoColumn v-model="item.host" />
            <OnlineSwitchTypeColumn
              v-model="item.online_switch_type"
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <BkFormItem class="ignore-biz">
          <BkCheckbox
            v-model="formData.force"
            v-bk-tooltips="t('强制切换，将忽略同步连接')"
            :false-label="false"
            true-label>
            <span class="safe-action-text">{{ t('强制切换') }}</span>
          </BkCheckbox>
        </BkFormItem>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type IValue } from '@components/instance-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import HostColumn from '@views/db-manage/redis/common/toolbox-field/host-column/Index.vue';

  import MasterSlaveInfoColumn from './components/MasterSlaveInfoColumn.vue';
  import OnlineSwitchTypeColumn from './components/OnlineSwitchTypeColumn.vue';

  interface IDataRow {
    host: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      master_instances: string[];
      related_clusters: {
        id: number;
        immute_domain: string;
      }[];
      slave_ip: string;
    };
    online_switch_type: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    host: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        master_instances: [] as string[],
        related_clusters: [] as IDataRow['host']['related_clusters'],
        slave_ip: '',
      },
      values.host,
    ),
    online_switch_type: values?.online_switch_type || '',
  });

  const createDefaultFormData = () => ({
    force: false,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Redis.MasterSlaveSwitch>(TicketTypes.REDIS_MASTER_SLAVE_SWITCH, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;
      Object.assign(formData, {
        force: details.force,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            host: {
              ip: infoItem.pairs[0].redis_master,
            } as IDataRow['host'],
            online_switch_type: infoItem.online_switch_type,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    force: boolean;
    infos: {
      cluster_ids: number[];
      online_switch_type: string;
      pairs: {
        redis_master: string;
        redis_slave: string;
      }[];
    }[];
  }>(TicketTypes.REDIS_MASTER_SLAVE_SWITCH);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  // 批量选择
  const handleHostBatchEdit = (list: IValue[]) => {
    const newList: IDataRow[] = [];
    list.forEach((proxyData) => {
      const { ip } = proxyData;
      if (!selectedMap.value[ip]) {
        newList.push(
          createRowData({
            host: {
              bk_cloud_id: proxyData.bk_cloud_id,
              bk_host_id: proxyData.bk_host_id,
              ip,
              master_instances: [],
              related_clusters: proxyData.related_clusters,
              slave_ip: '',
            },
          }),
        );
      }
    });
    formData.tableData = [...(formData.tableData[0].host.ip ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: string, field: string) => {
    formData.tableData.forEach((tableItem) => {
      Object.assign(tableItem, {
        [field]: value,
      });
    });
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          force: formData.force,
          infos: formData.tableData.map((tableItem) => ({
            cluster_ids: tableItem.host.related_clusters.map((item) => item.id),
            online_switch_type: tableItem.online_switch_type,
            pairs: [
              {
                redis_master: tableItem.host.ip,
                redis_slave: tableItem.host.slave_ip,
              },
            ],
          })),
        },
        ...formData.payload,
      });
    }
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .redis-master-failover-page {
    padding-bottom: 20px;

    // TODO 后续使用公共css
    .ignore-biz {
      width: fit-content;
    }

    .safe-action-text {
      padding-bottom: 2px;
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
