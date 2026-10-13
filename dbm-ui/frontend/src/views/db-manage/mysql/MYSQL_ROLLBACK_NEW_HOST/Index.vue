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
      :title="t('回档：按备份记录或指定时间恢复数据，支持新机构造、原地构造、库表闪回与记录级闪回。')" />
    <DbForm
      ref="formRef"
      class="mb-24 toolbox-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('时区')"
        required>
        <TimeZonePicker style="width: 450px" />
      </BkFormItem>
      <BkFormItem
        :label="t('回档类型')"
        required>
        <BkRadioGroup
          v-model="formData.rollbackType"
          style="width: 450px"
          type="card"
          @change="handleRollbackTypeChange">
          <BkRadioButton label="BUILD_INTO_NEW_CLUSTER">
            {{ t('新机构造回档') }}
          </BkRadioButton>
          <BkRadioButton label="BUILD_INTO_METACLUSTER">
            {{ t('原地构造回档') }}
          </BkRadioButton>
          <BkRadioButton label="TABLE_FLASHBACK">
            {{ t('库表闪回回档') }}
          </BkRadioButton>
          <BkRadioButton label="RECORD_FLASHBACK">
            {{ t('记录级闪回回档') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('回档方式')"
        required>
        <CardCheckbox
          v-model="formData.rollbackMethod"
          :desc="t('使用备份文件构造数据')"
          icon="bk-dbm-icon db-icon-form"
          :title="t('指定备份记录回档')"
          true-value="BACKUPID" />
        <CardCheckbox
          v-model="formData.rollbackMethod"
          class="ml-8"
          :desc="t('使用指定的时间最近的 全备+binlog 构造数据')"
          icon="bk-dbm-icon db-icon-time"
          :title="t('指定时间回档')"
          true-value="TIME" />
      </BkFormItem>
      <BkFormItem
        :label="t('备份源')"
        required>
        <BkRadioGroup v-model="formData.backupSource">
          <BkRadio :label="BackupSourceType.REMOTE">
            {{ t('远程备份') }}
          </BkRadio>
          <BkRadio :label="BackupSourceType.LOCAL">
            {{ t('本地备份') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <EditableTable
        :key="tableKey"
        ref="editableTableRef"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :label="t('源集群')"
            only-one-type
            :selected="selected"
            :tab-list-config="clusterSelectorConfig"
            @batch-edit="handleClusterBatchEdit" />
          <BackupRecordColumn
            v-if="formData.rollbackMethod === 'BACKUPID'"
            v-model="item.backupRecord"
            v-model:table-data="formData.tableData"
            :backup-source="formData.backupSource"
            :cluster="item.cluster" />
          <TimeBackupRecordColumn
            v-if="formData.rollbackMethod === 'TIME'"
            ref="timeBackupRecordColumnRef"
            v-model:backup-record="item.backupRecord"
            v-model:backup-time="item.backupTime"
            v-model:table-data="formData.tableData"
            :backup-source="formData.backupSource"
            :cluster="item.cluster" />
          <DbNameColumn
            v-model="item.databases"
            :cluster-id="item.cluster?.id"
            field="databases"
            :label="t('源 DB')"
            readonly
            required />
          <TableNameColumn
            v-model="item.tables"
            :cluster-id="item.cluster?.id"
            field="tables"
            :label="t('源表')"
            readonly
            required />
          <AffectDbColumn
            v-model="item.affectDb"
            :cluster="item.cluster"
            :enabled="isPhysicalBackup(item)" />
          <TargetSpecColumn :specs="targetSpecLists[index]" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleLabelsBatchEdit" />
          <AvailableResourceColumn :params="getAvailableResourceParams(item, index)" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </DbForm>
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
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { type Mysql } from '@services/model/ticket/ticket';
  import { filterClusters } from '@services/source/dbbase';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';
  import { isUnbound } from '@views/db-manage/common/machineSpecs';
  import AffectDbColumn from '@views/db-manage/common/toolbox-field/column/affect-db-column/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import TargetSpecColumn from '@views/db-manage/common/toolbox-field/column/target-spec-column/Index.vue';
  import type { TargetSpecItem } from '@views/db-manage/common/toolbox-field/column/target-spec-column/types';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';
  import BackupRecordColumn from '@views/db-manage/mysql/MYSQL_FIXPOINT_EXIST_CLUSTER/components/backup-record-column/Index.vue';
  import TimeBackupRecordColumn from '@views/db-manage/mysql/MYSQL_FIXPOINT_EXIST_CLUSTER/components/time-backup-record-column/Index.vue';

  import { random } from '@utils';

  /** 目标规格：只读派生，除展示字段外还需要规格 id 用于资源预览 */
  interface TargetSpecData extends TargetSpecItem {
    specId: number;
  }

  interface RowData {
    affectDb: string[];
    backupRecord: ComponentProps<typeof BackupRecordColumn>['modelValue'];
    backupTime: string;
    cluster: TendbhaModel;
    databases: string[];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    tables: string[];
  }

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();
  const router = useRouter();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  /** 各集群类型的角色顺序（上 -> 下）与展示名 */
  const roleConfigMap = {
    [ClusterTypes.TENDBHA]: [
      {
        machineType: MachineTypes.MYSQL_PROXY,
        name: 'Proxy',
      },
      {
        machineType: MachineTypes.MYSQL_BACKEND,
        name: 'Backend',
      },
    ],
    [ClusterTypes.TENDBSINGLE]: [
      {
        machineType: MachineTypes.SINGLE,
        name: 'Orphan',
      },
    ],
  } as Record<
    string,
    {
      machineType: MachineTypes;
      name: string;
    }[]
  >;

  const clusterSelectorConfig = {
    [ClusterTypes.TENDBHA]: {
      id: ClusterTypes.TENDBHA,
      multiple: false,
      name: 'TenDBHA',
    },
    [ClusterTypes.TENDBSINGLE]: {
      id: ClusterTypes.TENDBSINGLE,
      multiple: false,
      name: 'TenDBSingle',
    },
  };

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    affectDb: (data.affectDb || []) as string[],
    backupRecord: Object.assign({} as RowData['backupRecord'], data.backupRecord),
    backupTime: data.backupTime || '',
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
      } as TendbhaModel,
      data.cluster,
    ),
    // 新机构造回档为整库恢复，源 DB、源表锁定 *
    databases: ['*'],
    labels: (data.labels || []) as RowData['labels'],
    tables: ['*'],
  });

  const formRef = useTemplateRef('formRef');
  const editableTableRef = useTemplateRef('editableTableRef');
  const timeBackupRecordColumnRef =
    useTemplateRef<InstanceType<typeof TimeBackupRecordColumn>[]>('timeBackupRecordColumnRef');

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    payload: createTicketPayload(),
    rollbackMethod: 'BACKUPID' as 'BACKUPID' | 'TIME',
    rollbackType: 'BUILD_INTO_NEW_CLUSTER',
    tableData: [createTableRow()],
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const replaceTableData = (data: RowData[]) => {
    formData.tableData = data;
    tableKey.value = random();
  };

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));

  /**
   * 只读派生目标规格：
   * 1. 一种绑定规格 -> 该规格
   * 2. TenDBHA Backend 多种规格 -> 当前 Master 的绑定规格
   * 3. 其余角色多种规格 -> 已绑定规格中台数最多的一条，并列取规格名升序第一条（后端已排好序）
   */
  const getTargetSpecList = (cluster: TendbhaModel): TargetSpecData[] => {
    if (!cluster.id) {
      return [];
    }
    const roleConfigList = roleConfigMap[cluster.cluster_type] || roleConfigMap[ClusterTypes.TENDBHA];
    return roleConfigList.reduce<TargetSpecData[]>((acc, roleConfig) => {
      const specs = (cluster.machine_specs || []).filter((item) => item.machine_type === roleConfig.machineType);
      if (specs.length < 1) {
        return acc;
      }
      const count =
        roleConfig.machineType === MachineTypes.MYSQL_PROXY
          ? 2
          : specs.reduce((total, item) => total + item.count, 0);
      const boundSpecs = specs.filter((item) => !isUnbound(item));
      let specId = boundSpecs[0]?.spec_ids[0] || 0;
      let specName = boundSpecs[0] ? boundSpecs[0].spec_name : '';
      // 仅多规格的 TenDBHA Backend 改取当前 Master，其余保留后端排序后的第一条。
      if (
        boundSpecs.length > 1 &&
        roleConfig.machineType === MachineTypes.MYSQL_BACKEND &&
        cluster.cluster_type === ClusterTypes.TENDBHA
      ) {
        const masterSpec = cluster.masters[0]?.spec_config;
        specId = masterSpec?.id || 0;
        specName = masterSpec?.name || '';
      }
      acc.push({
        count,
        role: roleConfig.name,
        sourceSpecs:
          boundSpecs.length > 1
            ? boundSpecs.map((item) => ({
                count: item.count,
                name: item.spec_name,
              }))
            : undefined,
        specId,
        specName,
      });
      return acc;
    }, []);
  };

  // 规格仅随行内集群数据派生，展示与资源预览共用同一结果。
  const targetSpecLists = computed(() => formData.tableData.map((row) => getTargetSpecList(row.cluster)));

  /** 资源预览按主行（角色顺序第一条）将申领规格 + 资源标签筛选 */
  const getAvailableResourceParams = (row: RowData, index: number) => {
    const [firstSpec] = targetSpecLists.value[index];
    return {
      for_bizs: [currentBizId, 0],
      labels: row.labels.map((item) => item.id).join(','),
      resource_types: [DBTypes.MYSQL, 'PUBLIC'],
      spec_id: firstSpec?.specId || 0,
    };
  };

  const isPhysicalBackup = (row: RowData) => row.backupRecord?.backup_type === 'physical';

  useTicketDetail<Mysql.ResourcePool.RollbackNewHost>(TicketTypes.MYSQL_ROLLBACK_NEW_HOST, {
    async onSuccess(ticketDetail) {
      const { clusters, infos } = ticketDetail.details;
      const [info] = infos;
      const [cluster] = await filterClusters<TendbhaModel>({
        bk_biz_id: ticketDetail.bk_biz_id,
        cluster_ids: String(info.cluster_id),
      });
      Object.assign(formData, {
        backupSource: info.rollback_type.startsWith('LOCAL_') ? BackupSourceType.LOCAL : BackupSourceType.REMOTE,
        payload: createTicketPayload(ticketDetail),
        rollbackMethod: info.rollback_type.endsWith('_AND_TIME') ? 'TIME' : 'BACKUPID',
      });
      // 先完成方式切换引起的重置，再回填行数据。
      await nextTick();
      replaceTableData([
        createTableRow({
          affectDb: info.affect_database_list || [],
          backupRecord: info.backupinfo,
          backupTime: info.rollback_time || '',
          cluster: cluster || {
            master_domain: clusters?.[info.cluster_id]?.immute_domain || '',
          },
          labels: (info.label?.labels || []).map((id, index) => ({
            id,
            value: info.label?.label_names[index] || '',
          })),
        }),
      ]);
      await nextTick();
      if (formData.rollbackMethod === 'TIME') {
        timeBackupRecordColumnRef.value?.[0]?.flush();
      }
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: [Mysql.ResourcePool.RollbackNewHost['infos'][number]];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_ROLLBACK_NEW_HOST);

  // 切换构造方式、备份源时重置表格
  watch(
    () => [formData.rollbackMethod, formData.backupSource],
    () => {
      tableKey.value = random();
      formData.tableData = [createTableRow()];
    },
  );

  const handleRollbackTypeChange = (type: string) => {
    if (type === 'TABLE_FLASHBACK' || type === 'RECORD_FLASHBACK') {
      router.push({
        name: TicketTypes.MYSQL_FLASHBACK,
        query: {
          type,
        },
      });
    } else if (type === 'BUILD_INTO_METACLUSTER') {
      router.push({
        name: TicketTypes.MYSQL_ROLLBACK,
      });
    }
  };

  const handleClusterBatchEdit = (list: TendbhaModel[]) => {
    const [cluster] = list;
    if (cluster) {
      replaceTableData([createTableRow({ cluster })]);
    }
  };

  const handleLabelsBatchEdit = (labels: RowData['labels']) => {
    formData.tableData[0].labels = _.cloneDeep(labels);
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    await editableTableRef.value!.validate();
    const [item] = formData.tableData;
    return createTicketRun({
      details: {
        infos: [
          {
            // 逻辑备份的受影响库必须为空，不能提交源集群的全部 DB。
            affect_database_list: isPhysicalBackup(item) ? item.affectDb : [],
            backupinfo: item.backupRecord,
            cluster_id: item.cluster.id,
            databases: item.databases,
            databases_ignore: [],
            label: {
              label_names: item.labels.map((label) => label.value),
              labels: item.labels.map((label) => label.id),
            },
            rollback_time:
              formData.rollbackMethod === 'TIME' && item.backupTime ? formatDateToUTC(item.backupTime) : undefined,
            rollback_type:
              `${formData.backupSource.toUpperCase()}_AND_${formData.rollbackMethod}` as Mysql.ResourcePool.RollbackNewHost['infos'][number]['rollback_type'],
            tables: item.tables,
            tables_ignore: [],
          },
        ],
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
