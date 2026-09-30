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
      theme="info"
      :title="t('整机替换：替换所选主机，支持单节点以及主从集群的从库。')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="tableRef"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumnGroup
            v-model="item.host"
            :selected="selectedHosts"
            @batch-edit="handleBatchEditHost" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.ORACLE"
            :current-spec-id-list="[item.host.specId]"
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.resourceTags"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              for_bizs: [currentBizId, 0],
              labels: item.resourceTags.map((tag) => tag.id).join(','),
              resource_types: [DBTypes.ORACLE, 'PUBLIC'],
              spec_id: item.specId,
            }" />
        </EditableRow>
      </EditableTable>
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
<script setup lang="ts">
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Oracle } from '@services/model/ticket/ticket';
  import { getOracleHaInstanceList } from '@services/source/oracleHaCluster';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterInstStatusKeys, clusterTypeInfos, ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup from './components/HostColumnGroup.vue';
  import type { ReplaceHost, SelectorMachine, TicketInfo } from './types';
  import { buildHostInfo, computeReplicationSource, createReplaceHost } from './types';

  interface RowData {
    host: ReplaceHost;
    resourceTags: {
      id: number;
      value: string;
    }[];
    specId: number;
  }

  defineOptions({ name: TicketTypes.ORACLE_REPLACE_HOST });

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('tableRef');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: '10.1.20.31',
      key: 'ip',
      label: t('主机'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}): RowData => ({
    host: createReplaceHost(data.host),
    resourceTags: (data.resourceTags || []) as RowData['resourceTags'],
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selectedHosts = computed(() =>
    formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host),
  );

  // 回填：单据详情 infos 还原表格行
  useTicketDetail<Oracle.oracleReplaceHost>(TicketTypes.ORACLE_REPLACE_HOST, {
    onSuccess(ticketDetail) {
      const { db_version: dbVersion, infos } = ticketDetail.details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            // 协议回填：replace_host 为被替换主机，old_node 为复制源（携带主机要素）
            host: createReplaceHost({
              bk_biz_id: item.replace_host.bk_biz_id,
              bk_cloud_id: item.replace_host.bk_cloud_id,
              ip: item.replace_host.ip,
              port: item.replace_host.port,
              replication_source: {
                address: item.old_node.port ? `${item.old_node.ip}:${item.old_node.port}` : item.old_node.ip,
                bk_cloud_id: item.old_node.bk_cloud_id,
                bk_host_id: item.old_node.bk_host_id,
                ip: item.old_node.ip,
                port: item.old_node.port,
                role: item.old_node.role || '',
              },
              role: item.replace_host.role,
              version: (dbVersion || '').replace(/^Oracle-/, ''),
            }),
            resourceTags: (item.resource_spec.oracle.labels || []).map((labelId: string, index: number) => ({
              id: Number(labelId),
              value: item.resource_spec.oracle.label_names?.[index] || '',
            })),
            specId: item.resource_spec.oracle.spec_id,
          }),
        ),
      });
    },
  });

  // 两个场景共用 ORACLE_REPLACE_HOST 单据，仅 flow_type 区分：ORACLE_ADD_SLAVE（单节点/异常从库）与 ORACLE_ADD_SLAVE_VIA_CASCADING（主从正常从库，级联）
  const { loading: isSubmitting, run: runCreateTicket } = useCreateTicket<{
    db_version: string;
    flow_type: string;
    infos: TicketInfo[];
    ip_source: string;
  }>(TicketTypes.ORACLE_REPLACE_HOST);

  // 组装提交协议
  const buildDetails = (rows: RowData[], flowType: string) => ({
    db_version: `Oracle-${rows[0]?.host.version || ''}`,
    flow_type: flowType,
    infos: rows.map<TicketInfo>((item) => ({
      cluster_id: item.host.cluster_id,
      old_node: buildHostInfo(item.host.replication_source),
      replace_flag: true,
      // 页面所选主机（被替换主机）
      replace_host: buildHostInfo(item.host),
      resource_spec: {
        oracle: {
          count: 1,
          label_names: item.resourceTags.map((tag) => tag.value),
          labels: item.resourceTags.map((tag) => String(tag.id)),
          spec_id: item.specId,
        },
      },
    })),
    ip_source: 'resource_pool',
  });

  const handleSubmit = () => {
    tableRef.value!.validate().then(async () => {
      // 固定单行：主从集群且运行中的从库走级联（ORACLE_ADD_SLAVE_VIA_CASCADING，需反查主库），其余（单节点/异常从库）走 ORACLE_ADD_SLAVE
      const [row] = formData.tableData;
      if (!row) {
        return;
      }
      const isCascading =
        row.host.cluster_type === ClusterTypes.ORACLE_PRIMARY_STANDBY &&
        row.host.status === ClusterInstStatusKeys.RUNNING;

      if (!isCascading) {
        // 单节点与异常从库共用 flow_type=ORACLE_ADD_SLAVE
        await runCreateTicket({
          details: buildDetails([row], 'ORACLE_ADD_SLAVE'),
          ...formData.payload,
        });
        return;
      }

      // 级联场景反查主库实例填 old_master，反查失败则缺省（后端按 old_node 处理）
      const details = buildDetails([row], 'ORACLE_ADD_SLAVE_VIA_CASCADING');
      const [master] = (
        await getOracleHaInstanceList({
          cluster_id: row.host.cluster_id,
          role: 'primary',
        })
      ).results;
      if (master) {
        details.infos[0].old_master = buildHostInfo(master);
      }
      await runCreateTicket({ details, ...formData.payload });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  // 选择器确定：单选，选中主机替换唯一一行数据
  const handleBatchEditHost = (list: SelectorMachine[]) => {
    const [first] = list;
    if (!first) {
      return;
    }
    const instance = first.related_instances?.[0];
    const cluster = first.related_clusters?.[0];
    formData.tableData = [
      createTableRow({
        host: createReplaceHost({
          bk_cloud_id: first.bk_cloud_id,
          bk_host_id: first.bk_host_id,
          cluster_id: cluster?.id || 0,
          cluster_type: first.cluster_type as ClusterTypes,
          cluster_type_name:
            cluster?.cluster_type_name || clusterTypeInfos[first.cluster_type as ClusterTypes]?.name || '',
          instance_address: instance?.instance || '',
          ip: first.ip,
          master_domain: cluster?.immute_domain || '',
          port: instance?.port || 0,
          replication_source: computeReplicationSource({
            bk_cloud_id: first.bk_cloud_id,
            bk_host_id: first.bk_host_id,
            cluster_type: first.cluster_type,
            instance_address: instance?.instance,
            instance_role: first.instance_role,
            ip: first.ip,
            port: instance?.port,
            status: instance?.status,
          }),
          role: first.instance_role,
          specId: first.spec_id || instance?.spec_config?.id || 0,
          status: instance?.status || '',
          version: (cluster?.major_version || '').replace(/^Oracle-/, ''),
        }),
      }),
    ];
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    // ResourceTagColumn 批量填充 field 为 labels，映射到行字段 resourceTags
    const targetField = field === 'labels' ? 'resourceTags' : field;
    formData.tableData.forEach((item) => {
      Object.assign(item, { [targetField]: value });
    });
  };

  // 批量录入：固定单行，取首行输入替换表格数据
  const handleBatchInput = (data: Record<string, any>[]) => {
    const [first] = data;
    if (!first) {
      return;
    }
    formData.tableData = [
      createTableRow({
        host: createReplaceHost({
          ip: (first.ip as string) || '',
        }),
      }),
    ];
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'OracleToolboxIndex',
      });
    },
  });
</script>
