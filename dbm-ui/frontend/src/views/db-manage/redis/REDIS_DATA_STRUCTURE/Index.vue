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
    <div class="reids-data-structure-page">
      <BkAlert
        closable
        theme="info"
        :title="t('定点构造：按照指定历史时间点，把原集群或指定实例上的数据构造到新主机，产生新的构造实例')" />
      <div class="title-spot mt-12 mb-10">{{ t('时区') }}<span class="required" /></div>
      <TimeZonePicker
        class="mb-16"
        style="width: 450px" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          :key="tableKey"
          ref="editableTable"
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
              :label="t('架构版本')"
              readonly
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <MasterInstancesColumn
              v-model="item.master_instances"
              :cluster="item.cluster" />
            <SpecColumn
              v-model="item.cluster.cluster_spec.spec_id"
              :cluster-type="DBTypes.REDIS"
              field="cluster.cluster_spec.spec_id"
              label="规格需求"
              required
              :tooltips="t('默认使用部署时选定的规格，将从资源池自动匹配机器')" />
            <CountColumn
              v-model="item.count"
              :max="item.master_instances.length"
              @batch-edit="handleBatchEdit" />
            <RecoveryTimePointColumn
              v-model="item.recovery_time_point"
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
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

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import CountColumn from './components/CountColumn.vue';
  import MasterInstancesColumn from './components/MasterInstancesColumn.vue';
  import RecoveryTimePointColumn from './components/RecoveryTimePointColumn.vue';

  interface IDataRow {
    cluster: {
      bk_cloud_id: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      redis_master: RedisModel['redis_master'];
    };
    count: number;
    master_instances: string[];
    recovery_time_point: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
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
        redis_master: [] as RedisModel['redis_master'],
      },
      values.cluster,
    ),
    count: values.count || 1,
    master_instances: values.master_instances || [],
    recovery_time_point: values.recovery_time_point || '',
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  useTicketDetail<Redis.DataStructure>(TicketTypes.REDIS_DATA_STRUCTURE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            count: infoItem.resource_spec.redis.count,
            master_instances: infoItem.master_instances,
            recovery_time_point: infoItem.recovery_time_point,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      bk_cloud_id: number;
      cluster_id: number;
      master_instances: string[];
      recovery_time_point: string;
      resource_spec: {
        redis: {
          count: number;
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_DATA_STRUCTURE);

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
      key: 'master_domain',
      label: t('待构造的集群'),
    },
    {
      case: '192.168.10.2:10000,192.168.10.2:10000',
      key: 'master_instances',
      label: t('待构造的实例'),
    },
    {
      case: '1',
      key: 'count',
      label: t('构造主机数量'),
    },
    {
      case: '2025-03-11T10:26:13',
      key: 'recovery_time_point',
      label: t('构造到指定时间'),
    },
  ];

  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

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
              redis_master: item.redis_master,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          cluster: {
            master_domain: item.master_domain,
          } as IDataRow['cluster'],
          count: item.count ? Number(item.count) : 1,
          master_instances: item.master_instances ? item.master_instances.split(',') : [],
          recovery_time_point: item.recovery_time_point || '',
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
    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleBatchEdit = (value: string | number, field: string) => {
    formData.tableData.forEach((tableItem) => {
      Object.assign(tableItem, {
        [field]: value,
      });
    });
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            bk_cloud_id: tableItem.cluster.bk_cloud_id,
            cluster_id: tableItem.cluster.id,
            master_instances: tableItem.master_instances,
            recovery_time_point: formatDateToUTC(tableItem.recovery_time_point),
            resource_spec: {
              redis: {
                count: tableItem.count,
                spec_id: tableItem.cluster.cluster_spec.spec_id,
              },
            },
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .reids-data-structure-page {
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
