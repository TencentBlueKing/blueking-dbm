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
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MasterHostColumnGroup
            v-model="item.oldMaster"
            :selected="selected"
            @batch-edit="handleBatchEdit"
            @change="(data) => handleChange(data, item)" />
          <SlaveHostColumnGroup
            v-model="item.oldSlave"
            :master-host="item.oldMaster" />
          <Column
            :label="t('所属集群')"
            :min-width="150">
            <Block
              v-model="item.cluster.domain"
              :placeholder="t('自动生成')" />
          </Column>
          <SingleHost
            v-model="item.newMaster"
            field="newMaster"
            :label="t('新Master')"
            :min-width="150" />
          <SingleHost
            v-model="item.newSlave"
            field="newSlave"
            :label="t('新Slave')"
            :min-width="150" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <BackupSource v-model="formData.backupSource" />
      <TicketRemark v-model="formData.remark" />
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

  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import BackupSource from '@views/db-manage/common/toolbox-field/backup-source/Index.vue';
  import SingleHost from '@views/db-manage/common/toolbox-field/host-column/SingleHost.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/ticket-remark/Index.vue';

  import MasterHostColumnGroup, { type InputedHost, type SelectorHost } from './components/MasterHostColumnGroup.vue';
  import SlaveHostColumnGroup from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    oldMaster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      related_instances: string[];
    };
    oldSlave: RowData['oldMaster'];
    cluster: {
      id: number;
      domain: string;
    };
    newMaster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    newSlave: RowData['newMaster'];
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
        related_instances: [],
      },
      oldSlave: data.oldSlave || {
        ...initHost(),
        related_instances: [],
      },
      cluster: data.cluster || {
        id: 0,
        domain: '',
      },
      newMaster: data.newMaster || initHost(),
      newSlave: data.newSlave || initHost(),
    };
  };

  const defaultData = () => ({
    tableData: [createTableRow()],
    backupSource: BackupSourceType.LOCAL,
    remark: '',
  });

  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.oldMaster.bk_host_id).map((item) => item.oldMaster),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const rules = {
    'oldMaster.ip': [
      {
        validator: (value: string) => selected.value.filter((item) => item.ip === value).length < 2,
        message: t('目标主机重复'),
        trigger: 'change',
      },
    ],
  };

  interface ResourceHost {
    spec_id: number;
    hosts: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  }

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    backup_resource: BackupSourceType;
    ip_source: 'resource_pool';
    infos: {
      cluster_id: number;
      old_nodes: {
        old_master: ResourceHost['hosts'];
        old_slave: ResourceHost['hosts'];
      };
      resource_spec: {
        new_master: ResourceHost;
        new_slave: ResourceHost;
      };
    }[];
  }>(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun(
      {
        backup_resource: formData.backupSource,
        ip_source: 'resource_pool',
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          old_nodes: {
            old_master: [item.oldMaster],
            old_slave: [item.oldSlave],
          },
          resource_spec: {
            new_master: {
              spec_id: 0,
              hosts: [item.newMaster],
            },
            new_slave: {
              spec_id: 0,
              hosts: [item.newSlave],
            },
          },
        })),
      },
      formData.remark,
    );
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
              ip: item.ip,
              related_instances: item.related_instances.map((item) => item.instance),
            },
            cluster: {
              id: item.cluster_id,
              domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleChange = (data: InputedHost, row: RowData) => {
    row.cluster = {
      id: data.cluster_id,
      domain: data.master_domain,
    };
  };
</script>
