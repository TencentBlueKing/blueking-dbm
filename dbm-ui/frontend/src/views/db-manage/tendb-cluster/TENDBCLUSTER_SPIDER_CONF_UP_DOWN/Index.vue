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
  <SpiderWrapper>
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            allow-repeat
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <RoleColumn
            v-model="item.role"
            v-model:host-list="item.hostList"
            :cluster="item.cluster"
            @batch-edit="handleBatchEditColumn" />
          <EditableColumn
            :label="t('当前规格')"
            :min-width="200"
            readonly>
            <EditableBlock :placeholder="t('自动生成')">
              <p
                v-for="host in item.hostList"
                :key="host.bk_host_id">
                {{ host.ip }}（{{ host.spec_config?.name || '--' }}）
              </p>
            </EditableBlock>
          </EditableColumn>
          <SpecColumn
            v-model="item.specId"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :current-spec-id-list="item.hostList.map((item) => item.spec_config.id)"
            disabled-current-spec
            :machine-type="MachineTypes.TENDBCLUSTER_PROXY"
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.cluster.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem>
        <BkCheckbox
          v-model="formData.is_safe"
          :false-label="false"
          true-label>
          <span
            v-bk-tooltips="t('存在业务连接时需要人工确认')"
            class="safe-action-text">
            {{ t('检查业务连接') }}
          </span>
        </BkCheckbox>
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
      <template #action>
        <BkButton
          class="mr-8 w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbResetButton
          class="ml8"
          :confirm-handler="handleReset"
          :disabled="isSubmitting" />
      </template>
    </SmartAction>
  </SpiderWrapper>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';
  import SpiderWrapper from '@views/db-manage/tendb-cluster/TENDBCLUSTER_SPIDER_ADD_NODES/components/SpiderWrapper.vue';

  import { random } from '@utils';

  import RoleColumn from './components/RoleColumn.vue';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    hostList: TendbClusterModel['spider_master'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    role: string;
    specId: number;
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'spider.tendb-test.1.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'spider_master',
      key: 'role',
      label: t('节点类型'),
    },
    {
      case: '通用proxy配置',
      key: 'spec_name',
      label: t('目标规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
        spider_master: [] as TendbClusterModel['spider_master'],
        spider_slave: [] as TendbClusterModel['spider_slave'],
      } as unknown as TendbClusterModel,
      data.cluster,
    ),
    hostList: (data.hostList || []) as RowData['hostList'],
    labels: (data.labels || []) as RowData['labels'],
    role: data.role || '',
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    is_safe: true,
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.ResourcePool.SpiderConfUpDown>(TicketTypes.TENDBCLUSTER_SPIDER_CONF_UP_DOWN, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            cluster: {
              master_domain: details.clusters[item.cluster_id]?.immute_domain || '',
            },
            hostList: item.spider_old_ip_list.map((host) => ({
              bk_cloud_id: host.bk_cloud_id,
              bk_host_id: host.bk_host_id,
              ip: host.ip,
              spec_config: host.spec,
            })),
            labels: (item.resource_spec[item.switch_spider_role].labels || []).map((item) => ({ id: Number(item) })),
            role: item.switch_spider_role,
            specId: item.resource_spec[item.switch_spider_role].spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      old_nodes: {
        [x in string]: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      resource_spec: {
        [x in string]: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
      spider_old_ip_list: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        spec: TendbClusterModel['spider_master'][0]['spec_config'];
      }[];
      switch_spider_role: string;
    }[];
    ip_source: 'resource_pool';
    is_safe: boolean;
  }>(TicketTypes.TENDBCLUSTER_SPIDER_CONF_UP_DOWN);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          old_nodes: {
            [item.role]: item.hostList.map((host) => ({
              bk_cloud_id: host.bk_cloud_id,
              bk_host_id: host.bk_host_id,
              ip: host.ip,
            })),
          },
          resource_spec: {
            [item.role]: {
              count: item.hostList.length,
              label_names: item.labels.map((item) => item.value),
              labels: item.labels.map((item) => String(item.id)),
              spec_id: item.specId,
            },
          },
          spider_old_ip_list: item.hostList.map((host) => ({
            bk_cloud_id: host.bk_cloud_id,
            bk_host_id: host.bk_host_id,
            ip: host.ip,
            spec: host.spec_config,
          })),
          switch_spider_role: item.role,
        })),
        ip_source: 'resource_pool',
        is_safe: formData.is_safe,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          cluster: {
            master_domain: item.master_domain,
          },
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          role: item.role,
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
