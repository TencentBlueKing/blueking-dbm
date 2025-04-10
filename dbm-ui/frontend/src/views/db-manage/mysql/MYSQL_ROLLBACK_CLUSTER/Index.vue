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
    <div class="title-spot mt-12 mb-10">{{ t('时区') }}<span class="required" /></div>
    <TimeZonePicker style="width: 450px" />
    <div class="title-spot mt-12 mb-10">{{ t('构造类型') }}<span class="required" /></div>
    <BkRadioGroup
      v-model="rollbackClusterType"
      style="width: 450px"
      type="card">
      <BkRadioButton label="BUILD_INTO_NEW_CLUSTER">
        {{ t('构造到新集群') }}
      </BkRadioButton>
      <BkRadioButton label="BUILD_INTO_EXIST_CLUSTER">
        {{ t('构造到已有集群') }}
      </BkRadioButton>
      <BkRadioButton label="BUILD_INTO_METACLUSTER">
        {{ t('构造到原集群') }}
      </BkRadioButton>
    </BkRadioGroup>
    <BkForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <Component
        :is="tableMap[rollbackClusterType]"
        ref="table"
        :ticket-details="ticketDetails" />
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { type Mysql } from '@services/model/ticket/ticket';
  import type { BackupLogRecord } from '@services/source/fixpointRollback';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import BUILD_INTO_EXIST_CLUSTER from './components/BUILD_INTO_EXIST_CLUSTER/Index.vue';
  import BUILD_INTO_METACLUSTER from './components/BUILD_INTO_METACLUSTER/Index.vue';
  import BUILD_INTO_NEW_CLUSTER from './components/BUILD_INTO_NEW_CLUSTER/Index.vue';

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const tableMap = {
    BUILD_INTO_EXIST_CLUSTER,
    BUILD_INTO_METACLUSTER,
    BUILD_INTO_NEW_CLUSTER,
  };
  const defaultData = () => ({
    payload: createTickePayload(),
  });

  const rollbackClusterType =
    ref<Mysql.ResourcePool.RollbackCluster['rollback_cluster_type']>('BUILD_INTO_NEW_CLUSTER');
  const formData = reactive(defaultData());
  const ticketDetails = ref<Mysql.ResourcePool.RollbackCluster>();

  useTicketDetail<Mysql.ResourcePool.RollbackCluster>(TicketTypes.MYSQL_ROLLBACK_CLUSTER, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      rollbackClusterType.value = ticketDetail.details.rollback_cluster_type;
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
      });
      nextTick(() => {
        ticketDetails.value = details;
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      backupinfo?: BackupLogRecord; // 如果备份类型为REMOTE_AND_BACKUPID提供集群备份信息
      cluster_id: number;
      databases?: string[];
      databases_ignore?: string[];
      // 回档到新主机，指定机器需要填这个
      resource_spec?: {
        rollback_host: {
          count: number;
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: number;
        };
      };
      rollback_time?: string;
      rollback_type: string;
      tables?: string[];
      tables_ignore?: string[];
      target_cluster_id?: number; // 如果是回档到原集群 or 已有集群，需要填此参数
    }[];
    ip_source?: 'resource_pool'; // 只有在回档新集群选项，才传递此参数
    rollback_cluster_type: string;
  }>(TicketTypes.MYSQL_ROLLBACK_CLUSTER);

  const handleSubmit = async () => {
    const ticketDetails = await tableRef.value!.getValue();
    if (ticketDetails.infos.length) {
      createTicketRun({
        details: ticketDetails,
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableRef.value?.reset();
  };
</script>
