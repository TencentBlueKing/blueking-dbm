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
        class="toolbox-form mt-16 mb-24"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('升级类型')"
          property="updateType"
          required>
          <CardCheckbox
            v-model="formData.architectureType"
            :desc="t('如 TendisCache 等，迁移过程保持规格、版本不变')"
            icon="cluster"
            :title="t('集群架构')"
            true-value="cluster" />
          <CardCheckbox
            v-model="formData.architectureType"
            class="ml-8"
            :desc="t('支持部分或整机所有实例成对迁移至新主机，版本规格可变')"
            :disabled-tooltips="t('单节点仅支持原地升级')"
            icon="gaokeyong"
            :title="t('主从架构')"
            true-value="masterSlave" />
        </BkFormItem>
        <BkFormItem
          :label="t('迁移类型')"
          property="updateType"
          required>
          <CardCheckbox
            v-model="formData.migrateType"
            :desc="t('只迁移目标实例')"
            icon="fill-1"
            :title="t('实例迁移')"
            true-value="instance" />
          <CardCheckbox
            v-model="formData.migrateType"
            class="ml-8"
            :desc="t('主机关联的所有实例一并迁移')"
            :disabled="formData.architectureType === 'cluster'"
            icon="host"
            :title="t('整机迁移')"
            true-value="machine" />
        </BkFormItem>
        <Component
          :is="currentTable"
          ref="currentTable" />
        <TicketPayload v-model="formData" />
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
  import { BkFormItem } from 'bkui-vue/lib/form';
  import { useI18n } from 'vue-i18n';

  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import RenderClusterInstance from './components/cluseter-instance/Index.vue';
  import RenderMasterInstance from './components/master-slave-instance/Index.vue';
  import RenderMasterSlaveHost from './components/master-slave-machine/Index.vue';

  const { t } = useI18n();
  const router = useRouter();

  const currentTableRef = useTemplateRef('currentTable');

  // 单据克隆
  useTicketDetail<Redis.MigrateCluster>(TicketTypes.REDIS_CLUSTER_INS_MIGRATE, {
    onSuccess(cloneData) {
      currentTableRef.value!.setTableByTicketClone(cloneData);
      formData.remark = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  // 单据克隆
  useTicketDetail<Redis.MigrateSingle>(TicketTypes.REDIS_SINGLE_INS_MIGRATE, {
    onSuccess(cloneData) {
      formData.architectureType = 'masterSlave';
      const isDomain = cloneData.details.infos[0].display_info.migrate_type === 'domain';

      nextTick(() => {
        if (!isDomain) {
          formData.migrateType = 'machine';
        }
      });
      setTimeout(() => {
        currentTableRef.value!.setTableByTicketClone(cloneData);
        formData.remark = cloneData.remark;
        window.changeConfirm = true;
      });
    },
  });

  const { run: createClusterTicketRun, loading: isClusterSubmitting } = useCreateTicket<{
    infos: {
      cluster_id: number;
      resource_spec: {
        backend_group: {
          spec_id: number;
          count: number;
        };
      };
      old_nodes: {
        master: {
          bk_host_id: number;
          ip: string;
          port: number;
          bk_cloud_id: number;
          bk_biz_id: number;
        }[];
        slave: {
          bk_host_id: number;
          ip: string;
          port: number;
          bk_cloud_id: number;
          bk_biz_id: number;
        }[];
      };
      display_info: {
        instance: string;
        db_version: string[];
      };
    }[];
  }>(TicketTypes.REDIS_CLUSTER_INS_MIGRATE);

  const { run: createSingleTicketRun, loading: isSingleSubmitting } = useCreateTicket<{
    infos: {
      cluster_id: number;
      resource_spec: {
        backend_group: {
          spec_id: number;
          count: number;
        };
      };
      db_version: string;
      old_nodes: {
        master: {
          bk_host_id: number;
          ip: string;
          port: number;
          bk_cloud_id: number;
          bk_biz_id: number;
        }[];
        slave: {
          bk_host_id: number;
          ip: string;
          port: number;
          bk_cloud_id: number;
          bk_biz_id: number;
        }[];
      };
      display_info: {
        migrate_type: string; // domain | machine
        ip: string;
        domain: string;
      };
    }[];
  }>(TicketTypes.REDIS_SINGLE_INS_MIGRATE, {
    onSuccess(ticketId: number) {
      router.push({
        name: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
        params: {
          page: 'success',
        },
        query: {
          ticketId,
        },
      });
    },
  });

  const initFormData = () => ({
    architectureType: 'cluster', // cluster | masterSlave
    migrateType: 'instance', // instance | machine
    ...createTickePayload(),
  });

  const formData = reactive(initFormData());

  const renderKey = computed(() => `${formData.architectureType}-${formData.migrateType}`);

  const currentTable = computed(() => {
    const [architectureType, migrateType] = renderKey.value.split('-');
    if (architectureType === 'cluster') {
      return RenderClusterInstance;
    }

    if (migrateType === 'instance') {
      return RenderMasterInstance;
    }

    return RenderMasterSlaveHost;
  });

  const isSubmitting = computed(() => isClusterSubmitting.value || isSingleSubmitting.value);

  watch(
    () => formData.architectureType,
    () => {
      formData.migrateType = 'instance';
    },
  );

  watch(renderKey, () => {
    currentTable.value;
  });

  const handleSubmit = async () => {
    const runMap = {
      cluster: createClusterTicketRun,
      masterSlave: createSingleTicketRun,
    };

    const infos = await currentTableRef.value!.getValue();
    if (infos.length > 0) {
      runMap[formData.architectureType as keyof typeof runMap]({
        details: {
          infos,
        },
        remark: formData.remark,
      });
    }
  };

  const handleReset = () => {
    currentTableRef.value!.resetTable();
  };
</script>

<style lang="less" scoped>
  .redis-migrate {
    padding-bottom: 20px;

    .card-checkbox {
      width: 400px;
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
