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
  <UpgradeWrapper>
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
            ref="clusterRef"
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
            higher-sub-version />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem class="mb-8">
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
  </UpgradeWrapper>
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';
  import UpgradeWrapper from '@views/db-manage/tendb-cluster/TENDBCLUSTER_LOCAL_UPGRADE/components/UpgradeWrapper.vue';

  import { random } from '@utils';

  import CurrentVersionColumn from './components/CurrentVersionColumn.vue';
  import TargetVersionColumn from './components/TargetVersionColumn.vue';

  interface RowData {
    cluster: TendbClusterModel;
    current_version: ComponentProps<typeof CurrentVersionColumn>['modelValue'];
    new_db_module_id: number;
    pkg_id: number;
    target_version: ComponentProps<typeof TargetVersionColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
      } as TendbClusterModel,
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
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const batchInputConfig = [
    {
      case: 'spider.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
  ];

  const formData = reactive(defaultData());
  const tableKey = ref(random());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.RemoteUpgrade>(TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE, {
    onSuccess(ticketDetail) {
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
        is_check_process: ticketDetail.details.is_check_process,
        tableData: ticketDetail.details.infos.map((item) =>
          createTableRow({
            // 集群信息现查，从而带出当前版本信息
            cluster: {
              master_domain: ticketDetail.details.clusters[item.cluster_id].immute_domain,
            },
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
      pkg_id: number;
      target_version: {
        charset: string;
        db_module_name: string;
        db_version: string;
        pkg_name: string;
      };
    }[];
    is_check_process: boolean;
    upgrade_local: boolean;
  }>(TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster.id,
            current_version: item.current_version,
            new_db_module_id: item.new_db_module_id,
            pkg_id: item.pkg_id,
            target_version: item.target_version,
          })),
          is_check_process: formData.is_check_process,
          upgrade_local: true,
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
</script>
