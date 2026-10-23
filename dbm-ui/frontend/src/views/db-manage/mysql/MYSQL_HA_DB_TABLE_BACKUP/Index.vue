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
      :title="t('库表备份：指定库表备份，支持模糊匹配。')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16 toolbox-form"
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
            v-model="item.cluster"
            allow-repeat
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <EditableColumn
            :label="t('备份位置')"
            readonly
            :width="200">
            <EditableBlock :placeholder="t('自动生成')">
              {{ item.cluster.id ? (item.cluster.cluster_type === ClusterTypes.TENDBHA ? 'Slave' : 'Master') : '' }}
            </EditableBlock>
          </EditableColumn>
          <DbNameColumn
            v-model="item.db_patterns"
            :cluster-id="item.cluster?.id"
            field="db_patterns"
            :label="t('备份 DB 名')"
            required
            :rules="dbPatternsRepeatRules"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_dbs"
            :cluster-id="item.cluster?.id"
            field="ignore_dbs"
            :label="t('忽略 DB 名')"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.table_patterns"
            :cluster-id="item.cluster?.id"
            field="table_patterns"
            :label="t('备份表名')"
            required
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.ignore_tables"
            :cluster-id="item.cluster?.id"
            field="ignore_tables"
            :label="t('忽略表名')"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
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
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: TendbhaModel;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  }

  const { t } = useI18n();
  const router = useRouter();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '*',
      key: 'db_patterns',
      label: t('备份 DB 名'),
    },
    {
      case: 'NULL',
      key: 'ignore_dbs',
      label: t('忽略 DB 名'),
    },
    {
      case: '*',
      key: 'table_patterns',
      label: t('备份表名'),
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
    db_patterns: data.db_patterns || ['*'],
    ignore_dbs: data.ignore_dbs || [],
    ignore_tables: data.ignore_tables || [],
    table_patterns: data.table_patterns || ['*'],
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));

  // 「集群 + 备份 DB 名」组合判定键，任一列为空返回空串不参与判重；DB 按集合比较，与录入顺序无关
  const getRepeatKey = (row: RowData) =>
    row.cluster.master_domain && row.db_patterns.length > 0
      ? `${row.cluster.master_domain}#${[...new Set(row.db_patterns)].sort().join(',')}`
      : '';

  // 每行的组合键，只依赖集群域名与备份 DB 名，其它列变化不会触发重算
  const rowRepeatKeys = computed(() => formData.tableData.map(getRepeatKey));

  // 处于重复状态的组合键集合
  const getConflictKeys = (keys: string[]) => {
    const countMap = _.countBy(keys.filter(Boolean));
    return Object.keys(countMap).filter((key) => countMap[key] > 1);
  };

  const dbPatternsRepeatRules = [
    {
      message: t('cluster重复', [t('备份 DB 名')]),
      trigger: 'change',
      validator: (_value: string[], { rowData }: { rowData: RowData }) => {
        const key = getRepeatKey(rowData);
        return !key || formData.tableData.filter((item) => getRepeatKey(item) === key).length < 2;
      },
    },
  ];

  // 冲突是两行之间的关系，只改其中一行时另一行不会自己重校验，需要主动刷新：
  // 1. 组合键进入或离开冲突的行（另一行同时标红 / 同时消除）
  // 2. 组合键自身变了的行（如改了集群，DB 列不会自己重校验，旧的重复标红会残留）
  // 只刷新已填 DB 的行，避免把未填 DB 的行提前标红「DB 名不能为空」
  watch(rowRepeatKeys, (newKeys, oldKeys) => {
    const oldConflictKeys = getConflictKeys(oldKeys);
    const newConflictKeys = getConflictKeys(newKeys);
    const changedConflictKeys = new Set(_.xor(oldConflictKeys, newConflictKeys));
    const rowIndexList = formData.tableData.reduce<number[]>((result, row, index) => {
      const key = newKeys[index];
      if (row.db_patterns.length > 0 && (key !== oldKeys[index] || changedConflictKeys.has(key))) {
        result.push(index);
      }
      return result;
    }, []);
    if (rowIndexList.length < 1) {
      return;
    }
    nextTick(() => {
      // 校验不通过时 reject(false) 即标红本身，无需处理；其它异常照常抛出
      tableRef.value?.validateByField('db_patterns', rowIndexList).catch((error: unknown) => {
        if (error !== false) {
          throw error;
        }
      });
    });
  });

  useTicketDetail<Mysql.HaDBTableBackup>(TicketTypes.MYSQL_HA_DB_TABLE_BACKUP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((item) => ({
          cluster: {
            master_domain: clusters[item.cluster_id].immute_domain || '',
          },
          db_patterns: item.db_patterns,
          ignore_dbs: item.ignore_dbs,
          ignore_tables: item.ignore_tables,
          table_patterns: item.table_patterns,
        })),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      db_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
    }[];
  }>(TicketTypes.MYSQL_HA_DB_TABLE_BACKUP);

  const handleSubmit = () => {
    tableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster.id,
            db_patterns: item.db_patterns,
            ignore_dbs: item.ignore_dbs,
            ignore_tables: item.ignore_tables,
            table_patterns: item.table_patterns,
          })),
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      acc.push(
        createTableRow({
          cluster,
        }),
      );
      return acc;
    }, []);
    // 追加模式：选择器只回传本次勾选，不按已有集群过滤（重复由主键列校验提示），丢弃主键为空的行
    formData.tableData = [...formData.tableData.filter((item) => item.cluster.master_domain), ...dataList];
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
        db_patterns: item.db_patterns ? item.db_patterns.split(',') : [],
        ignore_dbs: item.ignore_dbs ? item.ignore_dbs.split(',') : [],
        ignore_tables: item.ignore_tables ? item.ignore_tables.split(',') : [],
        table_patterns: item.table_patterns ? item.table_patterns.split(',') : [],
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
