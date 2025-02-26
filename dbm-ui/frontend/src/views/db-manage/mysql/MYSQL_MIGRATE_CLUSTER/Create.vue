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
      <strong class="mirgate-types-title">
        {{ t('迁移类型') }}
      </strong>
      <div class="mt-8 mb-20">
        <CardCheckbox
          v-model="migrateType"
          :desc="t('只迁移目标集群')"
          icon="rebuild"
          :title="t('集群迁移')"
          :true-value="MigrateTypes.CLUSTER_MIGRATE" />
        <CardCheckbox
          v-model="migrateType"
          class="ml-8"
          :desc="t('主机关联的所有集群一并迁移')"
          icon="host"
          :title="t('整机迁移')"
          :true-value="MigrateTypes.HOST_MIGRATE" />
      </div>
    </div>
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <Component
        :is="tableComponentMap[migrateType]"
        ref="table"
        :data="formData.tableData" />
      <BackupSource v-model="formData.backupSource" />
      <TicketPayload v-model="formData" />
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
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterMigrateTable from './components/ClusterMigrateTable.vue';
  import HostMigrateTable from './components/HostMigrateTable.vue';
  import { MigrateTypes } from './types';

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const tableComponentMap = {
    [MigrateTypes.CLUSTER_MIGRATE]: ClusterMigrateTable,
    [MigrateTypes.HOST_MIGRATE]: HostMigrateTable,
  };

  const migrateType = ref(MigrateTypes.CLUSTER_MIGRATE);

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    tableData: [],
    ...createTickePayload(),
  });

  const formData = reactive(defaultData());

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: string;
    infos: {
      cluster_ids: number[];
      display_info: {
        type: MigrateTypes;
      };
      resource_spec: {
        new_master: {
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: 0;
        };
        new_slave: {
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: 0;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_MIGRATE_CLUSTER);

  const handleSubmit = async () => {
    const infos = await tableRef.value!.getValue();
    if (infos.length) {
      createTicketRun({
        details: {
          backup_source: formData.backupSource,
          infos,
          ip_source: 'resource_pool',
        },
        remark: formData.remark,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>

<style lang="less" scoped>
  .mirgate-types-title {
    position: relative;
    font-size: @font-size-mini;
    color: @title-color;

    &::after {
      position: absolute;
      top: 2px;
      right: -8px;
      color: @danger-color;
      content: '*';
    }
  }
</style>
