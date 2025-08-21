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
  <SmartAction class="db-toolbox mysql-checksum-page">
    <BkAlert
      class="mb-20"
      closable
      :title="t('数据校验修复_对集群的主库和从库进行数据一致性校验和修复_其中MyISAM引擎库表不会被校验和修复')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16 checksum-form toolbox-form"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            ref="clusterRef"
            v-model="item.cluster"
            :cluster-types="[ClusterTypes.TENDBHA]"
            allow-repeat
            :selected="selected"
            :rowspan="item.rowspan"
            @batch-edit="handleBatchEditCluster" />
          <MasterSlaveColumn
            v-model:slaves="item.slaves"
            v-model:master="item.master"
            v-model:table-data="formData.tableData"
            :cluster="item.cluster"
            @change="handleRowMerge" />
          <DbNameColumn
            v-model="item.db_patterns"
            :cluster-id="item.cluster?.id"
            field="db_patterns"
            :label="t('校验 DB 名')"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_dbs"
            :cluster-id="item.cluster?.id"
            field="ignore_dbs"
            :label="t('忽略 DB 名')"
            :required="false"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.table_patterns"
            :cluster-id="item.cluster?.id"
            field="table_patterns"
            :label="t('校验表名')"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.ignore_tables"
            :cluster-id="item.cluster?.id"
            field="ignore_tables"
            :required="false"
            :label="t('忽略表名')"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <BkFormItem
        :label="t('定时执行时间')"
        property="timing"
        required>
        <div class="time-box">
          <TimeZonePicker style="width: 350px" />
          <BkDatePicker
            v-model="formData.timing"
            class="ml-8"
            :disabled-date="disabledDate"
            :placeholder="t('请选择xx', [t('定时执行时间')])"
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
          style="width: 200px"
          suffix="h"
          type="number" />
      </BkFormItem>
      <BkFormItem
        :label="t('数据修复')"
        required>
        <BkSwitcher
          v-model="formData.data_repair.is_repair"
          theme="primary" />
      </BkFormItem>
      <BkFormItem
        v-if="formData.data_repair.is_repair"
        :label="t('修复模式')"
        required>
        <BkRadioGroup
          v-model="formData.data_repair.mode"
          class="repair-mode">
          <div class="item-box">
            <BkRadio label="manual">
              <div class="item-content">
                <DbIcon
                  class="item-flag"
                  type="account" />
                <div class="item-label">
                  {{ t('人工确认') }}
                </div>
                <div>{{ t('校验检查完成需人工确认后_方可执行修复动作') }}</div>
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
                <div>{{ t('校验检查完成后_将自动修复数据') }}</div>
              </div>
            </BkRadio>
          </div>
        </BkRadioGroup>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';
  import { format } from 'date-fns';
  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/edit-table-column/DbNameColumn.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/edit-table-column/TableNameColumn.vue';
  import { random } from '@utils';

  import MasterSlaveColumn from './components/MasterSlaveColumn.vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  interface RowData {
    cluster: TendbhaModel;
    table_patterns: string[];
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    slaves: ComponentProps<typeof MasterSlaveColumn>['slaves'];
    master: ComponentProps<typeof MasterSlaveColumn>['master'];
    rowspan: number;
  }

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const tableRef = useTemplateRef('table');
  const clusterRef = ref<InstanceType<typeof ClusterColumn>[]>();
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '192.168.10.2:20000,192.168.10.2:20001',
      key: 'slaves',
      label: t('校验从库'),
    },
    {
      case: 'NULL(自动生成)',
      key: 'master',
      label: t('校验主库'),
    },
    {
      case: '*',
      key: 'db_patterns',
      label: t('校验 DB 名'),
    },
    {
      case: 'NULL',
      key: 'ignore_dbs',
      label: t('忽略 DB 名'),
    },
    {
      case: '*',
      key: 'table_patterns',
      label: t('校验表名'),
    },
    {
      case: 'NULL',
      key: 'ignore_tables',
      label: t('忽略表名'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.cluster,
    ),
    table_patterns: data.table_patterns || ['*'],
    db_patterns: data.db_patterns || ['*'],
    ignore_dbs: data.ignore_dbs || [],
    ignore_tables: data.ignore_tables || [],
    slaves: data.slaves || ([] as RowData['slaves']),
    rowspan: data.rowspan || 1,
    master: Object.assign(
      {
        instance_address: '',
        id: 0,
        ip: '',
        port: 0,
        bk_cloud_id: 0,
        bk_biz_id: 0,
        bk_host_id: 0,
      } as ComponentProps<typeof MasterSlaveColumn>['master'],
      data.master,
    ),
  });

  const disabledDate = (date: Date | number) => {
    const day = new Date();
    day.setDate(day.getDate() - 1);
    const dateTime = typeof date === 'number' ? date : date.getTime();
    return dateTime < day.getTime();
  };

  const getCurrentDate = () => {
    const today = new Date();
    today.setMinutes(today.getMinutes() + 10);
    today.setSeconds(0);
    return today;
  };

  const defaultData = () => ({
    force: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
    data_repair: {
      is_repair: true,
      mode: 'manual',
    },
    runtime_hour: 48,
    timing: getCurrentDate(),
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  // 行合并
  const handleRowMerge = () => {
    const clusterMap: Record<string, RowData[]> = {};
    formData.tableData.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const { id } = item.cluster;
      if (!clusterMap[id]) {
        clusterMap[id] = [item];
      } else {
        clusterMap[id].push(item);
      }
    });
    Object.values(clusterMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
    });
  };

  useTicketDetail<Mysql.CheckSum>(TicketTypes.MYSQL_CHECKSUM, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => ({
          cluster: {
            master_domain: clusters[item.cluster_id].immute_domain || '',
          },
          table_patterns: item.table_patterns ? [item.table_patterns] : [],
          db_patterns: item.db_patterns ? [item.db_patterns] : [],
          ignore_dbs: item.ignore_dbs ? [item.ignore_dbs] : [],
          ignore_tables: item.ignore_tables ? [item.ignore_tables] : [],
          master: {
            instance_address: `${item.master.ip}:${item.master.port}`,
            ip: item.master.ip,
            port: item.master.port,
            bk_cloud_id: item.master.bk_cloud_id,
            bk_biz_id: item.master.bk_biz_id,
            bk_host_id: item.master.bk_host_id,
          },
          slaves: item.slaves.map((slave) => ({
            instance_address: `${slave.ip}:${slave.port}`,
            ip: slave.ip,
            port: slave.port,
            bk_cloud_id: slave.bk_cloud_id,
            bk_biz_id: slave.bk_biz_id,
            bk_host_id: slave.bk_host_id,
          })),
        })),
      });
      handleRowMerge();
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    data_repair: {
      is_repair: boolean;
      mode: string;
    };
    remark: string;
    runtime_hour: number;
    timing: string;
    infos: {
      cluster_id: number;
      master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      };
      slaves: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      db_patterns: string[];
      ignore_dbs: string[];
      table_patterns: string[];
      ignore_tables: string[];
    }[];
  }>(TicketTypes.MYSQL_CHECKSUM);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        data_repair: formData.data_repair,
        remark: formData.payload.remark,
        runtime_hour: formData.runtime_hour,
        timing: formatDateToUTC(format(new Date(formData.timing), 'yyyy-MM-dd HH:mm:ss')),
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          table_patterns: item.table_patterns,
          db_patterns: item.db_patterns,
          ignore_dbs: item.ignore_dbs,
          ignore_tables: item.ignore_tables,
          master: item.master,
          slaves: item.slaves,
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            cluster,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        cluster: {
          master_domain: item.master_domain,
        } as TendbhaModel,
        table_patterns: item.table_patterns ? [item.table_patterns] : [],
        db_patterns: item.db_patterns ? [item.db_patterns] : [],
        ignore_dbs: item.ignore_dbs ? [item.ignore_dbs] : [],
        ignore_tables: item.ignore_tables ? [item.ignore_tables] : [],
        slaves: item.slaves
          ? item.slaves.split(',')?.map((instance: string) => ({
              instance_address: instance,
            }))
          : [],
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };
</script>
<style lang="less">
  .mysql-checksum-page {
    .checksum-form {
      width: 100%;
      margin-top: 24px;
      margin-bottom: 32px;

      :deep(.bk-form-label) {
        font-weight: bold;
        color: @title-color;

        &::after {
          line-height: unset;
        }
      }

      .time-box {
        display: flex;
        align-items: center;
      }
    }

    .repair-mode {
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

          :deep(.bk-radio-input) {
            margin-top: 2px;
          }
        }
      }
    }
  }
</style>
