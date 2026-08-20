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
      :title="t('单节点迁移：支持实时同步数据和仅迁移表结构。实时同步数据需要开启 binlog。')" />
    <DbForm
      class="toolbox-form mb-20"
      form-type="vertical">
      <BkFormItem
        :label="t('迁移方式')"
        required>
        <div class="card-checkbox-block">
          <CardCheckbox
            v-model="migrateType"
            class="mb-8"
            :desc-list="[
              t('功能说明：将指定实例从当前主机迁移至新主机'),
              t('应用场景：用于“多实例共享主机” 场景下的拆分'),
            ]"
            icon="bk-dbm-icon db-icon-plus-fill"
            :title="t('实例迁移')"
            true-value="instance" />
          <CardCheckbox
            v-model="migrateType"
            class="mb-8 ml-8"
            :desc-list="[
              t('功能说明：将主机上的所有实例整体迁移到新机器，新机器可以更换规格'),
              t('应用场景：用于裁撤主机迁移，待裁撤主机需处于正常状态'),
            ]"
            icon="bk-dbm-icon db-icon-minus-fill"
            :title="t('整机迁移')"
            true-value="machine" />
          <CardCheckbox
            v-model="migrateType"
            class="mb-8"
            :desc-list="[
              t('功能说明：将故障主机进行原规格更换，故障主机上所有实例将迁移至新主机'),
              t('应用场景：用于故障主机替换'),
            ]"
            icon="bk-dbm-icon db-icon-shengji"
            :title="t('故障迁移')"
            true-value="failover" />
        </div>
      </BkFormItem>
      <Component
        :is="comMap[migrateType]"
        :key="formKey"
        ref="formRef" />
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
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { type Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import { random } from '@utils';

  import InstanceMigrate from './instance-migrate/Index.vue';
  import MachineMigrate from './machine-migrate/Index.vue';
  import RestoreSwitch from './restore-switch/Index.vue';

  const { t } = useI18n();
  const router = useRouter();

  const comMap = {
    failover: RestoreSwitch,
    instance: InstanceMigrate,
    machine: MachineMigrate,
  };

  const migrateType = ref<keyof typeof comMap>('instance');
  const formKey = ref(random());
  const formRef = ref<{
    getValue: () => Promise<{
      details: Mysql.ResourcePool.MigrateSingle;
      remark: string;
    }>;
  }>();

  useTicketDetail<Mysql.ResourcePool.MigrateSingle>(TicketTypes.MYSQL_MIGRATE_SINGLE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      migrateType.value = details.migrate_type;
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<Mysql.ResourcePool.MigrateSingle>(
    TicketTypes.MYSQL_MIGRATE_SINGLE,
  );

  const handleSubmit = async () => {
    const ticketDetail = await formRef.value?.getValue();
    if (ticketDetail) {
      createTicketRun({
        details: ticketDetail.details,
        remark: ticketDetail.remark,
      });
    }
  };

  const handleReset = () => {
    formKey.value = random();
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
<style lang="less" scoped>
  .card-checkbox-block {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
</style>
