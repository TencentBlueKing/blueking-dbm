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
      :title="t('数据校验修复：对集群的主库和从库进行数据一致性校验和修复，其中 MyISAM 引擎库表不会被校验和修复')" />
    <BkForm
      class="mb-20 form-block"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <ScopeColumn
            v-model="item.scope"
            :cluster="item.cluster"
            @batch-edit="handleBatchEdit" />
          <SlaveColumn
            v-model="item.slave"
            :row-data="item" />
          <MasterColumn
            v-model="item.master"
            :row-data="item" />
          <TagDbNameColumn
            v-model="item.dbPatterns"
            check-exist
            :cluster-id="item.cluster.id"
            field="dbPatterns"
            :label="t('备份DB名')"
            required
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.ignoreDbs"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="ignoreDbs"
            :label="t('忽略DB名')"
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.tablePatterns"
            check-exist
            :cluster-id="item.cluster.id"
            field="tablePatterns"
            :label="t('备份表名')"
            required
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.ignoreTables"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="ignoreTables"
            :label="t('忽略表名')"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <BkFormItem
        :label="t('指定执行时间')"
        property="timing"
        required>
        <div class="time-box">
          <TimeZonePicker style="width: 350px" />
          <BkDatePicker
            v-model="formData.timing"
            style="width: 360px"
            type="datetime" />
        </div>
      </BkFormItem>
      <BkFormItem
        :label="t('全局超时时间')"
        property="runtime_hour"
        required>
        <BkInput
          v-model="formData.runtime_hour"
          :max="168"
          :min="24"
          style="width: 360px"
          suffix="h"
          type="number" />
      </BkFormItem>
      <BkFormItem
        :label="t('修复数据')"
        property="data_repair.is_repair"
        required>
        <BkSwitcher
          v-model="formData.data_repair.is_repair"
          theme="primary" />
      </BkFormItem>
      <BkFormItem
        v-if="formData.data_repair.is_repair"
        :label="t('修复模式')"
        property="data_repair.mode">
        <BkRadioGroup
          v-model="formData.data_repair.mode"
          class="repair-mode-block">
          <div class="item-box">
            <BkRadio label="manual">
              <div class="item-content">
                <DbIcon
                  class="item-flag"
                  type="manual" />
                <div class="item-label">
                  {{ t('人工确认') }}
                </div>
                <div>{{ t('校验检查完成后，需人工确认后，方可执行修复动作') }}</div>
              </div>
            </BkRadio>
          </div>
          <div class="item-box">
            <BkRadio label="auto">
              <div class="item-content">
                <DbIcon
                  class="item-flag"
                  type="timed-task" />
                <div class="item-label">
                  {{ t('自动修复') }}
                </div>
                <div>{{ t('校验检查完成后，将自动修复数据') }}</div>
              </div>
            </BkRadio>
          </div>
        </BkRadioGroup>
      </BkFormItem>
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
  import dayjs from 'dayjs';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TagDbNameColumn from '@views/db-manage/common/toolbox-field/column/tag-db-name-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import MasterColumn from './components/MasterColumn.vue';
  import ScopeColumn from './components/ScopeColumn.vue';
  import SlaveColumn from './components/SlaveColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
    };
    scope: string;
    slave: string[];
    master: string[];
    dbPatterns: string[];
    ignoreDbs: string[];
    tablePatterns: string[];
    ignoreTables: string[];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
    },
    scope: data.scope || '',
    slave: data.slave || [],
    master: data.master || [],
    dbPatterns: data.dbPatterns || [],
    ignoreDbs: data.ignoreDbs || [],
    tablePatterns: data.tablePatterns || [],
    ignoreTables: data.ignoreTables || [],
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    data_repair: {
      is_repair: true,
      mode: 'manual',
    },
    is_sync_non_innodb: true,
    timing: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    runtime_hour: 48,
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      backup_infos: {
        master: string;
        slave: string;
        db_patterns: string[];
        table_patterns: string[];
        ignore_dbs: string[];
        ignore_tables: string[];
      }[];
      cluster_id: number;
      checksum_scope: string;
    }[];
    data_repair: {
      is_repair: boolean;
      mode: string;
    };
    is_sync_non_innodb: boolean;
    runtime_hour: number;
    timing: string;
    remark: string;
  }>(TicketTypes.TENDBCLUSTER_CHECKSUM);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          checksum_scope: item.scope,
          backup_infos: item.slave.map((slaveItem, index) => ({
            master: item.master[index],
            slave: slaveItem,
            db_patterns: item.dbPatterns,
            table_patterns: item.tablePatterns,
            ignore_dbs: item.ignoreDbs,
            ignore_tables: item.ignoreTables,
          })),
        })),
        data_repair: formData.data_repair,
        is_sync_non_innodb: formData.is_sync_non_innodb,
        runtime_hour: formData.runtime_hour,
        timing: formData.timing,
        remark: formData.remark,
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      item[field as keyof RowData] = value;
    });
  };
</script>
<style lang="less" scoped>
  .form-block {
    :deep(.bk-form-label) {
      font-size: 12px;
      font-weight: bold;
      color: #313238;
    }

    .time-box {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .repair-mode-block {
      flex-direction: column;

      .item-box {
        & ~ .item-box {
          margin-top: 20px;
        }

        .item-content {
          position: relative;
          padding-left: 25px;
          font-size: 12px;
          line-height: 20px;
          color: #63656e;
        }

        .item-flag {
          position: absolute;
          left: 3px;
          font-size: 18px;
          color: #979ba5;
        }

        .item-label {
          font-weight: bold;
        }

        .bk-radio {
          align-items: flex-start;

          .bk-radio-input {
            margin-top: 2px;
          }
        }
      }
    }
  }
</style>
