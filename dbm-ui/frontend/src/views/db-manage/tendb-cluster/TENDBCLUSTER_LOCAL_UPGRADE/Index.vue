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
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('版本升级：小版本可直接升级，跨版本需通过迁移升级，迁修升级需要相应版本的模块')" />
    <BkRadioGroup
      v-model="tendbclusterType"
      style="width: 450px"
      type="card">
      <BkRadioButton label="SPIDER">
        {{ t('接入层') }}
      </BkRadioButton>
      <BkRadioButton
        disabled
        label="REMOTE">
        {{ t('存储层') }}
      </BkRadioButton>
    </BkRadioGroup>
    <div class="title-spot mt-12 mb-10">{{ t('升级类型') }}<span class="required" /></div>
    <div class="mt-8 mb-20">
      <CardCheckbox
        v-model="updateType"
        :desc="t('适用于小版本升级，如 3.6.1 -> 3.6.3 或 3.6.1 -> 3.7.3')"
        icon="rebuild"
        :title="t('原地升级')"
        :true-value="TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE" />
      <CardCheckbox
        v-model="updateType"
        class="ml-8"
        :desc="t('适用于大版本升级，如 spider1.x -> spider3.x')"
        icon="clone"
        :title="t('迁移升级')"
        :true-value="TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE" />
    </div>
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
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
      <BkFormItem>
        <BkCheckbox
          v-model="formData.isSafe"
          :false-label="false"
          true-label>
          <span
            class="safe-action-text"
            v-bk-tooltips="t('存在业务连接时需要人工确认')">
            {{ t('检查业务连接') }}
          </span>
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';

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
  const router = useRouter();

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
    isSafe: true,
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

  const tendbclusterType = ref<'SPIDER' | 'REMOTE'>('SPIDER');
  const updateType = ref<TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE | TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE>(
    TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE,
  );
  const formData = reactive(defaultData());
  const tableKey = ref(random());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.LocalUpgrade>(TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE, {
    onSuccess(ticketDetail) {
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
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
    is_safe: boolean;
  }>(TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE);

  watch(updateType, () => {
    if (updateType.value === TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE) {
      router.push({
        name: TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE,
      });
    }
  });

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
          is_safe: formData.isSafe,
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
