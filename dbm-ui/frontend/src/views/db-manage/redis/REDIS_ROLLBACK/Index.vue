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
    <div class="redis-rollback-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t(
            '备份恢复：按备份记录将集群数据恢复到临时实例，原集群不受影响；TendisSSD / TendisPlus 还可构造到指定时间。如需写回原集群，请使用「以构造实例恢复」',
          )
        " />
      <div class="title-spot mt-12 mb-10">
        {{ t('时区') }}
        <span class="required" />
      </div>
      <TimeZonePicker
        class="mb-16"
        style="width: 450px" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="formRef"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          :key="tableKey"
          ref="editableTableRef"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :label="t('待构造的集群')"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('架构类型')"
              readonly
              :width="180">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <BackupRecordColumn
              v-model="item.backupRecord"
              :cluster-id="item.cluster.id"
              :cluster-type="item.cluster.cluster_type"
              :precheck="item.precheck"
              @open="handleOpenSelector(item)" />
            <HostCountColumn
              v-model="item.hostCount"
              :max="getShardMax(item)" />
            <SpecColumn
              v-model="item.specId"
              :cluster-type="DBTypes.REDIS"
              :current-spec-id-list="item.cluster?.cluster_spec?.spec_id ? [item.cluster.cluster_spec.spec_id] : []"
              field="specId"
              :label="t('目标规格')"
              :machine-type="item.cluster.cluster_type ? specClusterMachineMap[item.cluster.cluster_type] : undefined"
              required
              selectable
              :tooltips="t('复用存储层规格；默认本行集群当前规格，候选同族已启用；未选集群时留空')"
              @batch-edit="handleBatchEdit" />
            <ResourceTagColumn
              v-model="item.labels"
              @batch-edit="handleBatchEdit" />
            <AvailableResourceColumn
              :params="{
                city: item.cluster.region,
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.REDIS, 'PUBLIC'],
                spec_id: item.specId,
                labels: item.labels.map((labelItem) => labelItem.id).join(','),
              }" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <BackupRecordSelector
      v-model:is-show="isSelectorShow"
      :cluster="{
        cluster_domain: currentRow?.cluster.master_domain || '',
        cluster_type: currentRow?.cluster.cluster_type || '',
        id: currentRow?.cluster.id || 0,
      }"
      :model-value="currentRow?.backupRecord || null"
      @update:model-value="handleSelectorConfirm" />
    <template #action>
      <BkButton
        class="w-88"
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

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import type { Redis } from '@services/model/ticket/ticket';
  import { getRollbackPrecheck } from '@services/source/redisRollback';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import type { ClusterTypes } from '@common/const';
  import { DBTypes, TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import {
    createBackupRecord,
    hasBinlog,
    type IBackupRecord,
    type IPrecheckResult,
    utcToLocal,
  } from './components/backup-record';
  import BackupRecordColumn from './components/BackupRecordColumn.vue';
  import BackupRecordSelector from './components/BackupRecordSelector.vue';
  import HostCountColumn from './components/HostCountColumn.vue';

  interface IDataRow {
    backupRecord: IBackupRecord | null;
    cluster: {
      bk_cloud_id: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      region: string;
    };
    hostCount: number;
    labels: {
      id: number;
      value: string;
    }[];
    precheck: IPrecheckResult;
    specId: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    backupRecord: values.backupRecord ? createBackupRecord(values.backupRecord) : null,
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_spec: {
          spec_id: 0,
        } as RedisModel['cluster_spec'],
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        region: '',
      },
      values.cluster,
    ),
    hostCount: values.hostCount || 1,
    labels: values.labels || [],
    precheck: values.precheck || { message: '', state: 'unset' as const },
    specId: values.specId || 0,
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();
  const router = useRouter();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  useTicketDetail<Redis.Rollback>(TicketTypes.REDIS_ROLLBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((infoItem) => {
          const clusterInfo = clusters[infoItem.cluster_id];
          return createRowData({
            backupRecord: createBackupRecord({
              allow_binlog_nonconsecutive: infoItem.allow_binlog_nonconsecutive,
              backup_identify: infoItem.backup_identify,
              current_shard_count: 0,
              recovery_time_point: infoItem.recovery_time_point ? utcToLocal(infoItem.recovery_time_point) : '',
              scope: infoItem.shard_values.length ? 'pick' : 'all',
              // 克隆单无法从 details 拿到分片数，重新打开选择器后会刷新
              shard_count: infoItem.shard_values.length,
              shard_values: infoItem.shard_values,
            }),
            cluster: {
              master_domain: clusterInfo.immute_domain,
            } as IDataRow['cluster'],
            hostCount: infoItem.resource_spec.redis.count,
            labels: (infoItem.resource_spec.redis.labels || []).map((label, labelIndex) => ({
              id: Number(label),
              value: (infoItem.resource_spec.redis.label_names || [])[labelIndex] || '',
            })),
            specId: infoItem.resource_spec.redis.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      allow_binlog_nonconsecutive: boolean;
      backup_identify: string;
      cluster_id: number;
      recovery_time_point?: string;
      resource_spec: {
        redis: {
          count: number;
          label_names: string[];
          labels: string[];
          spec_id: number;
        };
      };
      shard_values: string[];
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_ROLLBACK);

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
      key: 'master_domain',
      label: t('待构造的集群'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const editableTableRef = useTemplateRef('editableTableRef');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const isSelectorShow = ref(false);
  const currentRow = ref<IDataRow | null>(null);

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  // 参与构造的分片数 = 主机构造数量上限；-1 表示克隆单回填后上限未知，不联动
  const getShardMax = (rowItem: IDataRow) => {
    const record = rowItem.backupRecord;
    if (!record?.backup_identify) {
      return 0;
    }
    if (record.scope === 'all') {
      return record.shard_count || -1;
    }
    return record.shard_values.length;
  };

  const handleOpenSelector = (rowItem: IDataRow) => {
    if (!rowItem.cluster.id) {
      return;
    }
    currentRow.value = rowItem;
    isSelectorShow.value = true;
  };

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_spec: item.cluster_spec,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
              region: item.region,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          cluster: {
            master_domain: item.master_domain,
          } as IDataRow['cluster'],
          labels: ((item.labels as string)?.split(',').map((labelItem) => ({ value: labelItem })) ||
            []) as IDataRow['labels'],
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

  const handleBatchEdit = (value: string | number, field: string) => {
    formData.tableData.forEach((tableItem) => {
      Object.assign(tableItem, {
        [field]: value,
      });
    });
  };

  const precheckRequest = useRequest(getRollbackPrecheck, {
    manual: true,
  });

  // 选择器确认后写入行数据（watch 会自动触发预校验）
  const handleSelectorConfirm = (record: IBackupRecord | null) => {
    if (currentRow.value && record) {
      currentRow.value.backupRecord = record;
    }
  };

  // 预校验：按行发起，任一相关字段变更后重新校验
  const runPrecheck = (rowItem: IDataRow) => {
    const record = rowItem.backupRecord;
    if (!record?.backup_identify || !rowItem.cluster.id) {
      Object.assign(rowItem.precheck, { message: '', state: 'unset' });
      return;
    }
    const recordSnapshot = JSON.stringify(record);
    precheckRequest
      .runAsync({
        allow_binlog_nonconsecutive: record.allow_binlog_nonconsecutive,
        backup_identify: record.backup_identify,
        cluster_id: rowItem.cluster.id,
        // 构造到：按外层选择的时区转 UTC 后传给预校验
        recovery_time_point: record.recovery_time_point ? formatDateToUTC(record.recovery_time_point) : undefined,
        resource_spec: {
          redis: {
            count: rowItem.hostCount,
          },
        },
        shard_values: record.scope === 'pick' ? record.shard_values : [],
      })
      .then((result) => {
        // 仅当行内备份记录未再变更时回写结果，避免竞态
        if (JSON.stringify(rowItem.backupRecord) !== recordSnapshot) {
          return;
        }
        if (!result.exist) {
          Object.assign(rowItem.precheck, {
            message: result.errors.join('；'),
            state: 'fail',
          });
        } else if (result.warnings.length) {
          Object.assign(rowItem.precheck, {
            message: [...result.errors, ...result.warnings].join('；'),
            state: 'warning',
          });
        } else {
          Object.assign(rowItem.precheck, {
            message: '',
            state: 'pass',
          });
        }
      })
      .catch(() => {
        Object.assign(rowItem.precheck, {
          message: '',
          state: 'fail',
        });
      });
  };

  // 备份记录 / 构造范围 / 构造到 / binlog 勾选任一变更后重新预校验；集群解析完成（拿到 id）后同样重跑
  watch(
    () => formData.tableData.map((item) => `${item.cluster.id}_${JSON.stringify(item.backupRecord)}`),
    (newList, oldList) => {
      newList.forEach((snapshot, index) => {
        if (snapshot !== oldList?.[index]) {
          runPrecheck(formData.tableData[index]);
        }
      });
    },
  );

  const handleSubmit = () => {
    editableTableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            allow_binlog_nonconsecutive: tableItem.backupRecord!.allow_binlog_nonconsecutive,
            backup_identify: tableItem.backupRecord!.backup_identify,
            cluster_id: tableItem.cluster.id,
            // 构造到仅 TendisSSD / TendisPlus 支持，其他架构不传该字段；字段名待后端确认（接口文档缺失）
            ...(hasBinlog(tableItem.cluster.cluster_type)
              ? { recovery_time_point: formatDateToUTC(tableItem.backupRecord!.recovery_time_point) }
              : {}),
            resource_spec: {
              redis: {
                count: tableItem.hostCount,
                label_names: tableItem.labels.map((labelItem) => labelItem.value),
                labels: tableItem.labels.map((labelItem) => String(labelItem.id)),
                spec_id: tableItem.specId,
              },
            },
            shard_values: tableItem.backupRecord!.scope === 'pick' ? tableItem.backupRecord!.shard_values : [],
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'RedisToolboxIndex',
      });
    },
  });
</script>

<style lang="less">
  .redis-rollback-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
