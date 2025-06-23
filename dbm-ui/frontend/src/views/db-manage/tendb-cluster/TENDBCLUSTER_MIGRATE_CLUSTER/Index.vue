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
    <BkAlert
      class="mb-20"
      closable
      :title="t('迁移主从：主从机器上的所有实例成对迁移到新机器上，旧机器会下架掉。')" />
    <BkForm
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
          <MasterHostColumnGroup
            v-model="item.oldMaster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SlaveHostColumnGroup
            v-model="item.oldSlave"
            :master-host="item.oldMaster" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.oldMaster.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <SpecColumn
            v-model="item.specId"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :current-spec-id="item.oldMaster.spec_id" />
          <ResourceTagColumn
            v-model="item.labels"
            v-model:selected="item.labelSelected" />
          <AvailableResourceColumn
            :params="{
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BackupSource v-model="formData.backupSource" />
      <BkFormItem
        :label="t('数据校验')"
        property="need_checksum"
        required>
        <BkSwitcher
          v-model="formData.need_checksum"
          theme="primary" />
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
<script lang="ts" setup>
  import type { _DeepPartial } from 'pinia';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import MasterHostColumnGroup, { type SelectorHost } from './components/MasterHostColumnGroup.vue';
  import SlaveHostColumnGroup from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    labels: number[];
    labelSelected: ComponentProps<typeof ResourceTagColumn>['selected'];
    oldMaster: ComponentProps<typeof MasterHostColumnGroup>['modelValue'];
    oldSlave: ComponentProps<typeof SlaveHostColumnGroup>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: _DeepPartial<RowData> = {}) => ({
    labels: (data.labels as number[]) || ([] as number[]),
    labelSelected: [] as ComponentProps<typeof ResourceTagColumn>['selected'],
    oldMaster: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      ip: '',
      master_domain: '',
      spec_id: 0,
      ...data.oldMaster,
      related_instances: [] as string[],
    },
    oldSlave: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      ...data.oldSlave,
      related_instances: [] as string[],
    },
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    need_checksum: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.oldMaster.bk_host_id).map((item) => item.oldMaster),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<TendbCluster.ResourcePool.MigrateCluster>(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        backupSource: details.backup_source,
        need_checksum: details.need_checksum,
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            labels: (item.resource_spec.backend_group.labels || []).map((item) => Number(item)),
            oldMaster: {
              ip: item.old_nodes.old_master?.[0]?.ip || '',
            },
            oldSlave: {
              ip: item.old_nodes.old_slave?.[0]?.ip || '',
            },
            specId: item.resource_spec.backend_group.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_id: number;
      resource_spec: {
        backend_group: {
          count: number;
          label_values?: string[]; // 标签value列表，单据详情回显用
          labels?: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
    need_checksum: boolean;
  }>(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        backup_source: formData.backupSource,
        infos: formData.tableData.map((item) => ({
          cluster_id: item.oldMaster.cluster_id,
          old_nodes: {
            old_master: [item.oldMaster],
            old_slave: [item.oldSlave],
          },
          resource_spec: {
            backend_group: {
              count: 1,
              label_values: item.labelSelected.map((item) => item.value),
              labels: item.labels.map((item) => String(item)),
              spec_id: item.oldMaster.spec_id,
            },
          },
        })),
        ip_source: 'resource_pool',
        need_checksum: formData.need_checksum,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            oldMaster: {
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
