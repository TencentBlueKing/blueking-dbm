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
    <div class="redis-migrate">
      <BkAlert
        closable
        theme="info"
        :title="
          t(
            '集群架构：将集群的部分实例迁移到新机器，迁移保持规格、版本不变；主从架构：主从实例成对迁移到新机器上，可选择部分实例迁移，也可整机所有实例一起迁移。',
          )
        " />
      <DbForm
        class="toolbox-form mt-16 mb-20"
        form-type="vertical"
        :model="formData">
        <MigrateFormItems v-model="formData" />
        <Component
          :is="currentTable"
          ref="currentTable" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import MigrateFormItems, {
    ArchitectureType,
    MigrateType,
  } from '@views/db-manage/redis/common/toolbox-field/migrate-form-items/Index.vue';

  import RenderMasterInstance from './components/master-slave-instance/Index.vue';
  import RenderMasterSlaveHost from './components/master-slave-machine/Index.vue';

  const { t } = useI18n();

  const currentTableRef = useTemplateRef('currentTable');

  // 单据克隆
  useTicketDetail<Redis.MigrateSingle>(TicketTypes.REDIS_SINGLE_INS_MIGRATE, {
    onSuccess(ticketDetail) {
      if (ticketDetail.details.infos[0].display_info.migrate_type === 'machine') {
        formData.migrateType = MigrateType.MACHINE;
      }

      nextTick(() => {
        currentTableRef.value!.setTableByTicketClone(ticketDetail);
        formData.payload = createTickePayload(ticketDetail);
        window.changeConfirm = true;
      });
    },
  });

  const { loading: isSubmitting, run: createSingleTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      db_version: string;
      display_info: {
        domain: string;
        ip: string;
        migrate_type: string; // domain | machine
      };
      old_nodes: {
        master: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        slave: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
      };
      resource_spec: {
        backend_group: {
          count: number;
          spec_id: number;
        };
      };
    }[];
  }>(TicketTypes.REDIS_SINGLE_INS_MIGRATE);

  const initFormData = () => ({
    architectureType: ArchitectureType.MASTER_SLAVE,
    migrateType: MigrateType.INSTANCE,
    payload: createTickePayload(),
  });

  const formData = reactive(initFormData());

  const currentTable = computed(() => {
    if (formData.migrateType === MigrateType.INSTANCE) {
      return RenderMasterInstance;
    }
    return RenderMasterSlaveHost;
  });

  const handleSubmit = async () => {
    const infos = await currentTableRef.value!.getValue();
    if (infos.length > 0) {
      createSingleTicketRun({
        details: {
          infos,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    currentTableRef.value!.resetTable();
    window.changeConfirm = false;
  };
</script>
