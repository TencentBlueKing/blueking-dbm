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
            higher-major-version
            higher-sub-version />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.TENDBCLUSTER"
            :current-spec-id-list="item.cluster.spec_ids"
            :label="t('规格')"
            :machine-type="MachineTypes.TENDBCLUSTER_BACKEND" />
          <ResourceTagColumn v-model="item.labels" />
          <AvailableResourceColumn
            :params="{
              subzones: item.cluster.subzones,
              city: item.cluster.city,
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
      <BackupSource v-model="formData.backupSource" />
      <BkFormItem
        :label="t('数据校验')"
        property="need_checksum">
        <BkSwitcher
          v-model="formData.need_checksum"
          theme="primary" />
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
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';
  import UpgradeWrapper from '@views/db-manage/tendb-cluster/TENDBCLUSTER_LOCAL_UPGRADE/components/UpgradeWrapper.vue';
  import CurrentVersionColumn from '@views/db-manage/tendb-cluster/TENDBCLUSTER_REMOTE_UPGRADE/components/CurrentVersionColumn.vue';
  import TargetVersionColumn from '@views/db-manage/tendb-cluster/TENDBCLUSTER_REMOTE_UPGRADE/components/TargetVersionColumn.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    current_version: ComponentProps<typeof CurrentVersionColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    new_db_module_id: number;
    pkg_id: number;
    specId: number;
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
    specId: data.specId || 0,
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
    backupSource: BackupSourceType.REMOTE,
    is_check_process: true,
    need_checksum: true,
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
    roleType: 'remote',
    updateType: TicketTypes.TENDBCLUSTER_MIGRATE_UPGRADE,
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.ResourcePool.MigrateUpgrade>(TicketTypes.TENDBCLUSTER_MIGRATE_UPGRADE, {
    onSuccess(ticketDetail) {
      Object.assign(formData, {
        ...createTicketPayload(ticketDetail),
        backupSource: ticketDetail.details.backup_source,
        is_check_process: ticketDetail.details.is_check_process,
        need_checksum: ticketDetail.details.need_checksum,
        tableData: ticketDetail.details.infos.map((item) =>
          createTableRow({
            // 集群信息现查，从而带出当前版本信息
            cluster: {
              master_domain: ticketDetail.details.clusters[item.cluster_id].immute_domain,
            },
            labels: (item.resource_spec.backend_group?.labels || []).map((item) => ({
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
    backup_source: BackupSourceType;
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
        old_master: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        old_slave: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      pkg_id: number;
      remote_shard_num: number;
      resource_spec: {
        backend_group: {
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
    need_checksum: boolean;
  }>(TicketTypes.TENDBCLUSTER_MIGRATE_UPGRADE);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          backup_source: formData.backupSource,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster.id,
            current_version: item.current_version,
            new_db_module_id: item.new_db_module_id,
            old_nodes: {
              old_master: item.cluster.remote_db.map((host) => ({
                bk_cloud_id: host.bk_cloud_id,
                bk_host_id: host.bk_host_id,
                ip: host.ip,
              })),
              old_slave: item.cluster.remote_dr.map((host) => ({
                bk_cloud_id: host.bk_cloud_id,
                bk_host_id: host.bk_host_id,
                ip: host.ip,
              })),
            },
            pkg_id: item.pkg_id,
            remote_shard_num: item.cluster.remote_shard_num,
            resource_spec: {
              backend_group: {
                count: 1,
                label_names: item.labels.map((item) => item.value),
                labels: item.labels.map((item) => String(item.id)),
                spec_id: item.specId,
              },
            },
            target_version: item.target_version,
          })),
          ip_source: 'resource_pool',
          is_check_process: formData.is_check_process,
          need_checksum: formData.need_checksum,
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
