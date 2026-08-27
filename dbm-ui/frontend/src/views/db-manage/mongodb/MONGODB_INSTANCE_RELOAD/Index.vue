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
      class="mb-16"
      theme="info"
      :title="
        t(
          '对 MongoDB 实例执行滚动重启，按 RS 内串行、分片分阶段编排。适用于计划性重启维护；支持按集群、按主机、按实例三种模式提单。',
        )
      " />
    <BkForm
      class="toolbox-form mb-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('目标选择模式')"
        required>
        <CardCheckbox
          v-model="formData.targetSelectMode"
          class="mr-8 mb-8"
          :desc="t('选择集群，自动展开全部 mongod + mongos')"
          icon="cluster"
          :title="t('按集群')"
          true-value="cluster">
        </CardCheckbox>
        <CardCheckbox
          v-model="formData.targetSelectMode"
          class="mr-8 mb-8"
          :desc="t('输入主机 IP，展开该 IP 上全部实例')"
          icon="host"
          :title="t('按主机')"
          true-value="machine">
        </CardCheckbox>
        <CardCheckbox
          v-model="formData.targetSelectMode"
          class="mb-8"
          :desc="t('指定 IP:Port，仅重启选中的实例')"
          icon="single-node"
          :title="t('按实例')"
          true-value="instance">
        </CardCheckbox>
      </BkFormItem>
      <!-- 动态模式表格 -->
      <Component
        :is="modeComponent"
        ref="currentTableRef" />
      <BkFormItem :label="t('强制重启')">
        <BkSwitcher
          v-model="formData.force"
          theme="primary" />
        <span
          class="ml-8"
          style="font-size: 12px">
          {{ formData.force ? t('强制重启') : t('优雅重启（推荐）') }}
        </span>
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { type Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterModeTable from './components/cluster/Index.vue';
  import MachineModeTable from './components/host/Index.vue';
  import InstanceModeTable from './components/instance/Index.vue';

  const modeComponentMap = {
    cluster: ClusterModeTable,
    instance: InstanceModeTable,
    machine: MachineModeTable,
  };

  const { t } = useI18n();
  const route = useRoute();

  if (route.query.instances) {
  }

  const currentTableRef =
    useTemplateRef<ComponentExposed<typeof ClusterModeTable | typeof MachineModeTable | typeof InstanceModeTable>>(
      'currentTableRef',
    );

  // 默认表单数据
  const defaultData = () => ({
    force: false,
    payload: createTicketPayload(),
    targetSelectMode: route.query.instances ? 'instance' : ('cluster' as Mongodb.InstanceReload['target_select_mode']),
  });

  const formData = reactive(defaultData());

  // 当前模式的组件和数据计算属性
  const modeComponent = computed(() => modeComponentMap[formData.targetSelectMode] || ClusterModeTable);

  // 单据详情回显
  useTicketDetail<Mongodb.InstanceReload>(TicketTypes.MONGODB_INSTANCE_RELOAD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        force: details.force,
        payload: createTicketPayload(ticketDetail),
        targetSelectMode: details.target_select_mode,
      });
    },
  });

  // 创建工单
  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    force: Mongodb.InstanceReload['force'];
    infos: Mongodb.InstanceReload['infos'];
    target_select_mode: Mongodb.InstanceReload['target_select_mode'];
  }>(TicketTypes.MONGODB_INSTANCE_RELOAD);

  // 提交处理
  const handleSubmit = () => {
    const tableRef = currentTableRef.value;
    if (!tableRef) {
      return;
    }

    tableRef.validate().then(() => {
      console.log({
        details: {
          force: formData.force,
          infos: tableRef.getValue(),
          target_select_mode: formData.targetSelectMode,
        },
        ...formData.payload,
      });

      createTicketRun({
        details: {
          force: formData.force,
          infos: tableRef.getValue(),
          target_select_mode: formData.targetSelectMode,
        },
        ...formData.payload,
      });
    });
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
