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
      :title="
        t(
          '定点构造：新建一个单节点实例，通过全备 +binlog 的方式，将数据库恢复到过去的某一时间点或者某个指定备份文件的状态',
        )
      " />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('时区')"
        required>
        <TimeZonePicker style="width: 450px" />
      </BkFormItem>
      <TargetCluster
        ref="tableRef"
        v-model="formData.tableData" />
      <BkFormItem
        :label="t('构造新主机规格')"
        property="specId"
        required>
        <div class="mongo-dbstruct">
          <RenderTargetSpec
            ref="specProxyRef"
            v-model="formData.specId"
            :biz-id="bizId"
            :cloud-id="0"
            cluster-type="mongodb"
            machine-type="mongodb"
            :show-refresh="false" />
        </div>
      </BkFormItem>
      <BkFormItem
        :label="t('每台主机构造Shard数量')"
        property="shardNum"
        required>
        <div class="mongo-dbstruct">
          <BkInput
            v-model="formData.shardNum"
            :min="1"
            type="number" />
          <span class="need-tip">{{ t('共需n台主机', { n: needHostNum }) }}</span>
        </div>
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
  import { useI18n } from 'vue-i18n';

  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import RenderTargetSpec from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import TargetCluster, { type RowData } from './components/TargetCluster.vue';

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const defaultData = () => ({
    payload: createTickePayload(),
    shardNum: 1,
    specId: '',
    tableData: [] as RowData[],
  });

  const tableRef = ref();
  const formData = reactive(defaultData());

  const isShardCluster = computed(
    () => formData.tableData[0]?.cluster.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER,
  );
  const needHostNum = computed(() => {
    return isShardCluster.value
      ? Math.ceil((formData.tableData[0]?.cluster.shard_num || 1) / formData.shardNum)
      : Math.ceil(formData.tableData.length / formData.shardNum);
  });

  useTicketDetail<Mongodb.Restore>(TicketTypes.MONGODB_PITR_RESTORE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        shardNum: details.instance_per_host,
        specId: details.resource_spec.mongodb.spec_id,
        tableData: details.cluster_ids.map((clusterId) => ({
          cluster: Object.assign(details.clusters[clusterId], {
            master_domain: details.clusters[clusterId].immute_domain,
          }),
          rollback_time: details.rollback_time[clusterId],
        })),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_ids: number[];
    instance_per_host: number;
    resource_spec: {
      mongo_config?: {
        count: number;
        spec_id: number;
      };
      mongodb: {
        count: number;
        spec_id: number;
      };
      mongos?: {
        count: number;
        spec_id: number;
      };
    };
    rollback_time: Record<string, string>;
  }>(TicketTypes.MONGODB_PITR_RESTORE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const resourceSpec = {
      mongodb: {
        count: needHostNum.value,
        spec_id: formData.specId as unknown as number,
      },
    };
    if (isShardCluster.value) {
      Object.assign(resourceSpec, {
        mongo_config: {
          count: 1, // 固定为1
          spec_id: formData.tableData[0]?.cluster.mongo_config[0].spec_config.id, // 这个与回档集群的mongo_config规格一致
        },
        mongos: {
          count: 1, // 固定为1
          spec_id: formData.tableData[0]?.cluster.mongos[0].spec_config.id, // 这个与回档集群的mongos规格一致
        },
      });
    }
    createTicketRun({
      details: {
        cluster_ids: formData.tableData.map((item) => item.cluster.id),
        instance_per_host: formData.shardNum,
        resource_spec: resourceSpec,
        rollback_time: formData.tableData.reduce<Record<string, string>>((acc, item) => {
          Object.assign(acc, {
            [item.cluster.id]: formatDateToUTC(item.rollback_time),
          });
          return acc;
        }, {}),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
<style lang="less" scoped>
  .mongo-dbstruct {
    :deep(.bk-input) {
      width: 400px;
    }

    .need-tip {
      margin-left: 12px;
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
