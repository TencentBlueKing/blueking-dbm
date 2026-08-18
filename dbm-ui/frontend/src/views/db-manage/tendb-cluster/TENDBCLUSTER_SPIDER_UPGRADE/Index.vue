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
  <UpgradeWrapper v-model="wrapperController">
    <SmartAction class="db-toolbox">
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <CurrentVersionColumn
            v-model="item.current_version"
            :cluster="item.cluster" />
          <TargetVersionColumn
            v-model="item.target_version"
            v-model:new-db-module-id="item.new_db_module_id"
            v-model:pkg-id="item.pkg_id"
            :cluster="item.cluster"
            higher-major-version />
          <EditableColumn
            :label="t('规格')"
            :min-width="200"
            readonly>
            <EditableBlock :placeholder="t('自动生成')">
              <p v-if="item.cluster.spider_master?.[0]?.spec_config?.id">
                {{ item.cluster.spider_master[0]?.spec_config.name }}（spider_master）
              </p>
              <p v-if="item.cluster.spider_slave?.[0]?.spec_config?.id">
                {{ item.cluster.spider_slave[0]?.spec_config.name }}（spider_slave）
              </p>
            </EditableBlock>
          </EditableColumn>
          <ResourceTagColumn v-model="item.labels" />
          <AvailableResourceColumn
            :params="{
              subzones: item.cluster.subzones,
              city: item.cluster.city,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.cluster.spider_master?.[0]?.spec_config?.id || 0,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem>
        <BkCheckbox
          v-model="formData.is_check_process"
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
  </UpgradeWrapper>
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';
  import CurrentVersionColumn from '@views/db-manage/tendb-cluster/TENDBCLUSTER_LOCAL_UPGRADE/components/CurrentVersionColumn.vue';
  import TargetVersionColumn from '@views/db-manage/tendb-cluster/TENDBCLUSTER_LOCAL_UPGRADE/components/TargetVersionColumn.vue';
  import UpgradeWrapper from '@views/db-manage/tendb-cluster/TENDBCLUSTER_LOCAL_UPGRADE/components/UpgradeWrapper.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    current_version: ComponentProps<typeof CurrentVersionColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    new_db_module_id: number;
    pkg_id: number;
    target_version: ComponentProps<typeof TargetVersionColumn>['modelValue'];
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        city: '',
        id: 0,
        master_domain: '',
        spec_ids: [],
        subzones: '',
      } as unknown as RowData['cluster'],
      data.cluster,
    ),
    current_version: Object.assign(
      {
        charset: '',
        db_module_name: '',
        db_version: '',
        pkg_name: '',
      },
      data.current_version,
    ),
    labels: (data.labels || []) as RowData['labels'],
    new_db_module_id: data.new_db_module_id || 0,
    pkg_id: data.pkg_id || 0,
    target_version: Object.assign(
      {
        charset: '',
        db_module_name: '',
        db_version: '',
        pkg_name: '',
      },
      data.target_version,
    ),
  });

  const defaultData = () => ({
    is_check_process: true,
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const batchInputConfig = [
    {
      case: 'spider.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
  ];

  const wrapperController = ref({
    roleType: 'spider',
    updateType: TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE,
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.ResourcePool.SpiderUpgrade>(TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE, {
    onSuccess(ticketDetail) {
      Object.assign(formData, {
        ...createTicketPayload(ticketDetail),
        is_check_process: ticketDetail.details.is_check_process,
        tableData: ticketDetail.details.infos.map((item) =>
          createTableRow({
            // 集群信息现查，从而带出当前版本信息
            cluster: {
              master_domain: ticketDetail.details.clusters[item.cluster_id].immute_domain,
            },
            labels: (item.resource_spec.spider_master?.labels || []).map((item) => ({
              id: Number(item),
            })),
            new_db_module_id: item.new_db_module_id,
            pkg_id: item.pkg_id,
            target_version: item.target_version,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      current_version: {
        charset: string;
        db_module_name: string;
        db_version: string;
        pkg_name: string;
      };
      new_db_module_id: number;
      old_nodes: {
        spider_master: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        spider_slave: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      pkg_id: number;
      resource_spec: {
        [key in string]: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
      target_version: {
        charset: string;
        db_module_name: string;
        db_version: string;
        pkg_name: string;
      };
    }[];
    ip_source: 'resource_pool';
    is_check_process: boolean;
    upgrade_local: boolean;
  }>(TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      const resourceSpec = (rowData: RowData, role: 'spider_master' | 'spider_slave') => {
        const hostList = rowData.cluster[role];
        if (!hostList.length) {
          return {};
        }
        return {
          [role]: {
            count: hostList.length,
            label_names: rowData.labels.map((item) => item.value),
            labels: rowData.labels.map((item) => String(item.id)),
            spec_id: hostList?.[0]?.spec_config?.id,
          },
        };
      };
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster.id,
            current_version: item.current_version,
            new_db_module_id: item.new_db_module_id,
            old_nodes: {
              spider_master: item.cluster.spider_master.map((host) => ({
                bk_cloud_id: host.bk_cloud_id,
                bk_host_id: host.bk_host_id,
                ip: host.ip,
              })),
              spider_slave: item.cluster.spider_slave.map((host) => ({
                bk_cloud_id: host.bk_cloud_id,
                bk_host_id: host.bk_host_id,
                ip: host.ip,
              })),
            },
            pkg_id: item.pkg_id,
            resource_spec: {
              ...resourceSpec(item, 'spider_master'),
              ...resourceSpec(item, 'spider_slave'),
            },
            target_version: item.target_version,
          })),
          ip_source: 'resource_pool',
          is_check_process: formData.is_check_process,
          upgrade_local: false,
        },
        ...formData.payload,
      });
    }
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
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
