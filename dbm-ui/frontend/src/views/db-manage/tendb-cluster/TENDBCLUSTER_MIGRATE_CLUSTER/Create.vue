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
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BackupSource v-model="formData.backupSource" />
      <TicketPayload v-model="formData" />
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import MasterHostColumnGroup, { type SelectorHost } from './components/MasterHostColumnGroup.vue';
  import SlaveHostColumnGroup from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    oldMaster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      master_domain: string;
      related_instances: string[];
      spec_id: number;
    };
    oldSlave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      related_instances: string[];
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => {
    const initHost = () => ({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    });
    return {
      oldMaster: data.oldMaster || {
        ...initHost(),
        cluster_id: 0,
        master_domain: '',
        related_instances: [],
        spec_id: 0,
      },
      oldSlave: data.oldSlave || {
        ...initHost(),
        related_instances: [],
      },
    };
  };

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    tableData: [createTableRow()],
    ...createTickePayload(),
  });

  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.oldMaster.bk_host_id).map((item) => item.oldMaster),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  interface ResourceHost {
    hosts: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    spec_id: number;
  }

  useTicketDetail<TendbCluster.ResourcePool.MigrateCluster>(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { backup_source: backupSource, infos } = details;
      Object.assign(formData, {
        backupSource,
        tableData: infos.map((item) =>
          createTableRow({
            oldMaster: {
              ...item.old_nodes.old_master[0],
              cluster_id: 0,
              master_domain: '',
              related_instances: [],
              spec_id: 0,
            },
            oldSlave: {
              ...item.old_nodes.old_slave[0],
              related_instances: [],
            },
          }),
        ),
        ...createTickePayload(ticketDetail),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_resource: BackupSourceType;
    infos: {
      cluster_id: number;
      old_nodes: {
        old_master: ResourceHost['hosts'];
        old_slave: ResourceHost['hosts'];
      };
      resource_spec: {
        backend_group: {
          count: number;
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        backup_resource: formData.backupSource,
        infos: formData.tableData.map((item) => ({
          cluster_id: item.oldMaster.cluster_id,
          old_nodes: {
            old_master: [item.oldMaster],
            old_slave: [item.oldSlave],
          },
          resource_spec: {
            backend_group: {
              count: 1,
              spec_id: item.oldMaster.spec_id,
            },
          },
        })),
        ip_source: 'resource_pool',
      },
      remark: formData.remark,
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
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              ip: item.ip,
              master_domain: item.master_domain,
              related_instances: item.related_instances.map((item) => item.instance),
              spec_id: item.spec_id,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
