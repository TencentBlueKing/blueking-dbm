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
        t('迁移主从：集群主从实例将成对迁移至新机器。默认迁移同机所有关联集群，也可迁移部分集群，迁移会下架旧实例')
      " />
    <div>
      <div class="title-spot mt-12 mb-10">{{ t('迁移类型') }}<span class="required" /></div>
      <div class="mt-8 mb-20">
        <CardCheckbox
          v-model="operaObjectType"
          :desc="t('只迁移目标集群')"
          icon="rebuild"
          :title="t('集群迁移')"
          :true-value="OperaObejctType.CLUSTER" />
        <CardCheckbox
          v-model="operaObjectType"
          class="ml-8"
          :desc="t('主机关联的所有集群一并迁移')"
          icon="host"
          :title="t('整机迁移')"
          :true-value="OperaObejctType.MACHINE" />
      </div>
    </div>
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <div class="title-spot mt-12 mb-10">{{ t('主机选择方式') }}<span class="required" /></div>
      <BkRadioGroup
        v-model="sourceType"
        class="mb-16"
        :class="{
          'alert-show': sourceType === SourceType.RESOURCE_MANUAL,
        }"
        style="width: 450px"
        type="card"
        @change="handleChangeMode">
        <BkRadioButton :label="SourceType.RESOURCE_AUTO">
          {{ t('资源池自动匹配') }}
        </BkRadioButton>
        <BkRadioButton :label="SourceType.RESOURCE_MANUAL">
          {{ t('资源池手动选择') }}
        </BkRadioButton>
      </BkRadioGroup>
      <BkAlert
        v-if="sourceType === SourceType.RESOURCE_MANUAL"
        class="mt-8 mb-8"
        theme="warning"
        :title="t('“资源池手动选择”会丢失规格导致不能自愈，请谨慎操作！')" />
      <Component
        :is="comMap[operaObjectType]"
        :key="comKey"
        ref="table"
        :source-type="sourceType"
        :ticket-details="ticketDetails" />
      <BackupSource v-model="formData.backupSource" />
      <BkFormItem
        :label="t('数据校验')"
        property="need_checksum"
        required>
        <BkSwitcher
          v-model="formData.need_checksum"
          theme="primary" />
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
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType, OperaObejctType, SourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import ClusterMigrate from './components/cluster-migrate/Index.vue';
  import MachineMigrate from './components/machine-migrate/Index.vue';

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const comMap = {
    [OperaObejctType.CLUSTER]: ClusterMigrate,
    [OperaObejctType.MACHINE]: MachineMigrate,
  };

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    need_checksum: true,
    payload: createTickePayload(),
  });

  const sourceType = ref(SourceType.RESOURCE_AUTO);
  const formData = reactive(defaultData());
  const comKey = ref(random());
  const operaObjectType = ref<keyof typeof comMap>(OperaObejctType.CLUSTER);
  const ticketDetails = ref<Mysql.ResourcePool.MigrateCluster>();

  useTicketDetail<Mysql.ResourcePool.MigrateCluster>(TicketTypes.MYSQL_MIGRATE_CLUSTER, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { backup_source: backupSource, opera_object: operaObject } = details;
      Object.assign(formData, {
        backupSource,
        need_checksum: details.need_checksum,
        payload: createTickePayload(ticketDetail),
      });
      comKey.value = random();
      operaObjectType.value = operaObject;
      sourceType.value = details.source_type;
      setTimeout(() => {
        ticketDetails.value = details;
      }, 100);
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: string;
    infos: {
      cluster_ids: number[];
      resource_spec: {
        // 自动匹配走backend_group
        backend_group?: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
        // 手动选择走new_master、new_slave
        new_master?: {
          count: number;
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: number;
        };
        new_slave?: {
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
    }[];
    ip_source: 'resource_pool';
    need_checksum: boolean;
    opera_object: OperaObejctType;
    source_type: SourceType;
  }>(TicketTypes.MYSQL_MIGRATE_CLUSTER);

  const handleChangeMode = () => {
    comKey.value = random();
  };

  const handleSubmit = async () => {
    const infos = await tableRef.value!.getValue();
    if (infos.length) {
      createTicketRun({
        details: {
          backup_source: formData.backupSource,
          infos,
          ip_source: 'resource_pool',
          need_checksum: formData.need_checksum,
          opera_object: operaObjectType.value,
          source_type: sourceType.value,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableRef.value!.reset();
  };
</script>
<style lang="less">
  .alert-show {
    margin-bottom: 8px !important;
  }
</style>
