<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 * for the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <BkAlert
      class="mb-20"
      closable
      theme="info"
      :title="t('添加从库：为所选上游实例新增 1 个从库。')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('上游类型')"
        required>
        <div class="mode-cards">
          <CardCheckbox
            v-model="formData.mode"
            :desc="t('为主从集群的从库新增级联从库')"
            icon="bk-dbm-icon db-icon-kelong"
            :title="t('从库')"
            true-value="slave" />
          <CardCheckbox
            v-model="formData.mode"
            class="ml-8"
            :desc="t('为主从集群的主库新增从库')"
            icon="bk-dbm-icon db-icon-shengji"
            :title="t('主库')"
            true-value="master" />
          <CardCheckbox
            v-model="formData.mode"
            class="ml-8"
            :desc="t('为单节点新增从库，原实例升主')"
            icon="bk-dbm-icon db-icon-plus-fill"
            :title="t('单节点')"
            true-value="single" />
        </div>
      </BkFormItem>
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
          <UpstreamInstanceColumn
            v-model="item.upstreamInstance"
            :mode="formData.mode"
            :selected="selectedInstances"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="220"
            readonly>
            <EditableBlock :placeholder="t('自动生成')">
              {{
                item.upstreamInstance.ip && item.upstreamInstance.master_domain
                  ? item.upstreamInstance.master_domain
                  : ''
              }}
            </EditableBlock>
          </EditableColumn>
          <ReplicationSourceColumn
            v-if="formData.mode === 'master'"
            v-model="item.copySource"
            :cluster-id="item.upstreamInstance.cluster_id" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.ORACLE"
            :current-spec-id-list="[item.upstreamInstance.spec_config.id as number]"
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.resourceTags"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn :params="getAvailableResourceParams(item)" />
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
  import { getOracleHaClusterList } from '@services/source/oracleHaCluster';
  import { getOracleSingleClusterList } from '@services/source/oracleSingleCluster';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import ReplicationSourceColumn from './components/ReplicationSourceColumn.vue';
  import UpstreamInstanceColumn from './components/UpstreamInstanceColumn.vue';
  import type { HostInfo, UpstreamInstance, UpstreamMode } from './types';
  import { buildHostInfo, createUpstreamInstance } from './types';

  interface RowData {
    // 复制源（主库卡片由后端数据推导，单节点/从库卡片为空）
    copySource: {
      address: string;
      master: HostInfo | null;
      node: HostInfo | null;
      role: string;
    };
    resourceTags: {
      id: number;
      value: string;
    }[];
    specId: number;
    upstreamInstance: UpstreamInstance;
  }

  defineOptions({ name: TicketTypes.ORACLE_ADD_SLAVE });

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('tableRef');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: '192.168.10.2:1521',
      key: 'upstream_instance',
      label: t('上游实例'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}): RowData => ({
    copySource: Object.assign(
      {
        address: '',
        master: null as HostInfo | null,
        node: null as HostInfo | null,
        role: '',
      },
      data.copySource,
    ),
    resourceTags: (data.resourceTags || []) as RowData['resourceTags'],
    specId: data.specId || 0,
    upstreamInstance: createUpstreamInstance(data.upstreamInstance),
  });

  const defaultData = () => ({
    mode: 'slave' as UpstreamMode,
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selectedInstances = computed(() =>
    formData.tableData.filter((item) => item.upstreamInstance.instance_address).map((item) => item.upstreamInstance),
  );

  // AvailableResourceColumn 参数
  const getAvailableResourceParams = (item: RowData) => ({
    for_bizs: [currentBizId, 0],
    labels: item.resourceTags.map((tag) => tag.id).join(','),
    resource_types: [DBTypes.ORACLE, 'PUBLIC'],
    spec_id: item.specId,
  });

  const isApplying = ref(false);

  // 回填：ticket_type 恒为 ORACLE_ADD_SLAVE，上游类型靠 details.upstream_type 区分
  useTicketDetail<Oracle.oracleAddSlave>(TicketTypes.ORACLE_ADD_SLAVE, {
    onSuccess(ticketDetail) {
      isApplying.value = true;
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      // 回填上游类型：直接取协议 upstream_type，存量单据无该字段时回退 single
      Object.assign(formData, {
        mode: ['master', 'single', 'slave'].includes(details.upstream_type) ? details.upstream_type : 'slave',
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((item: any) =>
          createTableRow({
            copySource: {
              // 级联场景：old_master 为主库（复制源），old_node 为正常从库（上游实例）
              address: formatAddress(item.old_master),
              master: item.old_master ? buildHostInfo(item.old_master) : null,
              node: item.old_master ? buildHostInfo(item.old_node) : null,
              role: item.old_master ? 'primary' : '',
            },
            resourceTags: (item.resource_spec?.oracle?.labels || []).map((labelId: number, index: number) => ({
              id: Number(labelId),
              value: item.resource_spec?.oracle?.label_names?.[index] || '',
            })),
            specId: item.resource_spec?.oracle?.spec_id || 0,
            upstreamInstance: createUpstreamInstance({
              bk_biz_id: item.old_node?.bk_biz_id || window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.old_node?.bk_cloud_id || 0,
              bk_host_id: item.old_node?.bk_host_id || 0,
              cluster_id: item.cluster_id,
              instance_address: formatAddress(item.old_node),
              ip: item.old_node?.ip || '',
              master_domain: clusters?.[item.cluster_id]?.immute_domain || '',
              port: item.old_node?.port || 0,
              role: '',
              version: (details.db_version || '').replace(/^Oracle-/, ''),
            }),
          }),
        ),
      });
      nextTick(() => {
        isApplying.value = false;
      });
    },
  });

  // 兼容无 port 的存量单据：有 port 拼接 ip:port，否则仅展示 ip
  const formatAddress = (host?: { ip?: string; port?: number }) => {
    if (!host?.ip) {
      return '';
    }
    return host.port ? `${host.ip}:${host.port}` : host.ip;
  };

  const { loading: isSubmitting, run: runCreateTicket } = useCreateTicket<{
    // 前端拼接：Oracle-{实例版本号}
    db_version: string;
    flow_type: string;
    infos: {
      cluster_id: number;
      // 级联场景：old_node 为正常从库，old_master 为主库
      old_master?: HostInfo;
      old_node: HostInfo;
      replace_flag: boolean;
      resource_spec: {
        oracle: {
          count: number;
          label_names: string[];
          labels: string[];
          spec_id: number;
        };
      };
    }[];
    ip_source: string;
    // 上游类型：single 单节点 / master 主库 / slave 从库，供单据详情区分
    upstream_type: UpstreamMode;
  }>(TicketTypes.ORACLE_ADD_SLAVE);

  // 切换上游类型：重置表格并重新渲染，回填场景跳过
  watch(
    () => formData.mode,
    () => {
      if (isApplying.value) {
        return;
      }
      tableKey.value = random();
      formData.tableData = [createTableRow()];
    },
  );

  // 通过集群列表接口逐行获取 major_version 回填到 upstreamInstance.version（每行 cluster_id 对应一个 major_version）
  const fetchClusterMajorVersions = async () => {
    const rows = formData.tableData.filter((item) => item.upstreamInstance.cluster_id);
    await Promise.all(
      rows.map(async (item) => {
        const params = { id: item.upstreamInstance.cluster_id, limit: -1 };
        const results =
          formData.mode === 'single'
            ? (await getOracleSingleClusterList(params)).results
            : (await getOracleHaClusterList(params)).results;
        Object.assign(item.upstreamInstance, {
          version: (results[0]?.major_version || '').replace(/^Oracle-/, ''),
        });
      }),
    );
  };

  const handleSubmit = () => {
    tableRef.value!.validate().then(async () => {
      await fetchClusterMajorVersions();
      runCreateTicket({
        details: {
          // 后端要求前端拼接版本号：Oracle-{集群 major_version}
          db_version: `Oracle-${formData.tableData[0]?.upstreamInstance.version || ''}`,
          // 选择主库且从库正常（复制源为健康从库）时走级联；单节点/从库/主库从库异常走普通新增
          flow_type:
            formData.mode === 'master' && formData.tableData[0]?.copySource.node
              ? 'ORACLE_ADD_SLAVE_VIA_CASCADING'
              : 'ORACLE_ADD_SLAVE',
          infos: formData.tableData.map((item) => {
            // 级联场景：old_node 为正常从库，old_master 为主库；其余场景上游实例即 old_node
            const { node } = item.copySource;
            return {
              cluster_id: item.upstreamInstance.cluster_id,
              old_master: node ? buildHostInfo(item.upstreamInstance) : undefined,
              old_node: node ? buildHostInfo(node) : buildHostInfo(item.upstreamInstance),
              replace_flag: false,
              resource_spec: {
                oracle: {
                  count: 1,
                  label_names: item.resourceTags.map((tag) => tag.value),
                  labels: item.resourceTags.map((tag) => String(tag.id)),
                  spec_id: item.specId,
                },
              },
            };
          }),
          ip_source: 'resource_pool',
          // 上游类型：与卡片选择一致，单据详情据此区分
          upstream_type: formData.mode,
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  // 选择器确定：单选，选中实例替换唯一一行数据
  const handleBatchEdit = (list: any[]) => {
    const [first] = list;
    if (!first) {
      return;
    }
    formData.tableData = [
      createTableRow({
        upstreamInstance: {
          bk_cloud_id: first.bk_cloud_id || 0,
          bk_host_id: first.bk_host_id || 0,
          cluster_id: first.cluster_id,
          instance_address: first.instance_address,
          ip: first.ip,
          master_domain: first.master_domain,
          port: first.port,
          role: first.role,
          spec_config: { id: first.spec_config?.id || 0 },
          version: first.version || '',
        },
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
    const instanceAddress = (first.upstream_instance as string) || '';
    formData.tableData = [
      createTableRow({
        upstreamInstance: {
          instance_address: instanceAddress,
          ip: instanceAddress.split(':')[0] || '',
          port: Number(instanceAddress.split(':')[1]) || 0,
        },
      }),
    ];
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'OracleToolboxIndex',
      });
    },
  });
</script>
<style lang="less" scoped>
  .mode-cards {
    display: flex;
    align-items: stretch;
  }
</style>
