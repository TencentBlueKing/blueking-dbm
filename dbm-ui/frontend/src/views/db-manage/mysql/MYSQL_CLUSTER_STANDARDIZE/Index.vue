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
      :title="t('对已部署的集群重新进行标准化动作')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            ref="clusterRef"
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('集群类型')"
            :min-width="150"
            required>
            <EditableBlock :placeholder="t('自动生成')">
              {{ item.cluster.cluster_type_name || '' }}
            </EditableBlock>
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem class="mb-8">
        <BkCheckbox v-model="formData.with_push_config">
          {{ t('下发配置') }}
        </BkCheckbox>
      </BkFormItem>
      <BkFormItem class="mb-8">
        <BkCheckbox v-model="formData.with_deploy_binary">
          {{ t('推送二进制文件') }}
        </BkCheckbox>
      </BkFormItem>
      <BkFormItem class="mb-8">
        <BkCheckbox v-model="formData.with_cc_standardize">
          {{ t('CC 标准化') }}
        </BkCheckbox>
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { type Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: TendbhaModel;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.cluster,
    ),
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
    with_cc_standardize: false,
    with_deploy_binary: false,
    with_push_config: true,
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  useTicketDetail<Mysql.ClusterStandardize>(TicketTypes.MYSQL_CLUSTER_STANDARDIZE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.cluster_ids.map((id) =>
          createTableRow({
            cluster: {
              master_domain: clusters[id]?.immute_domain || '',
            },
          }),
        ),
        with_cc_standardize: details.with_cc_standardize,
        with_deploy_binary: details.with_deploy_binary,
        with_push_config: details.with_push_config,
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    bk_biz_id: number;
    cluster_ids: number[];
    with_cc_standardize: boolean; // 是否cc模块标准
    with_deploy_binary: boolean; // 是否推送二进制
    with_instance_standardize: boolean; // 是否实例标准化. 高危
    with_push_config: boolean; // 是否推送配置
  }>(TicketTypes.MYSQL_CLUSTER_STANDARDIZE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_ids: formData.tableData.map((item) => item.cluster.id),
        with_cc_standardize: formData.with_cc_standardize,
        with_deploy_binary: formData.with_deploy_binary,
        with_instance_standardize: false,
        with_push_config: formData.with_push_config,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbhaModel[]) => {
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
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
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
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };
</script>
