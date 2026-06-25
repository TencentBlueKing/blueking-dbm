<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <BkAlert
      class="mb-20"
      closable
      :title="t('下架运维节点：摘除指定集群的运维节点（spider_mnt 角色）实例')" />
    <DbForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MntNodeColumn
            v-model="item.mntNode"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.mntNode.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </DbForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import MntNodeColumn from './components/MntNodeColumn.vue';

  interface RowData {
    mntNode: ComponentProps<typeof MntNodeColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    mntNode: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: '',
      ip: '',
      master_domain: '',
      port: 0,
      role: '',
      ...data.mntNode,
    },
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() =>
    formData.tableData.filter((item) => item.mntNode.bk_host_id).map((item) => item.mntNode),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  useTicketDetail<TendbCluster.SpiderMntDestroy>(TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((info) => {
          const [firstNode] = info.spider_ip_list;
          return createTableRow({
            mntNode: {
              instance_address: `${firstNode.ip}:${firstNode.port || 0}`,
            },
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      spider_ip_list: {
        bk_cloud_id: number;
        ip: string;
        port: number;
      }[];
    }[];
    is_safe: boolean;
  }>(TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            cluster_id: item.mntNode.cluster_id,
            spider_ip_list: [
              {
                bk_cloud_id: item.mntNode.bk_cloud_id,
                ip: item.mntNode.ip,
                port: item.mntNode.port,
              },
            ],
          })),
          is_safe: true,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbClusterInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            mntNode: {
              instance_address: item.instance_address,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
