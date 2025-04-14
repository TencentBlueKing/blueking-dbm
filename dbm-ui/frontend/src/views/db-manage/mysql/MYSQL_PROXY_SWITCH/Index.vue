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
      :title="t('对集群的Proxy实例进行替换')" />
    <div>
      <div class="title-spot mt-12 mb-10">{{ t('替换类型') }}<span class="required" /></div>
      <div class="mt-8 mb-20">
        <CardCheckbox
          v-model="operaObjectType"
          :desc="t('只替换目标实例')"
          icon="rebuild"
          :title="t('实例替换')"
          :true-value="OperaObejctType.INSTANCE" />
        <CardCheckbox
          v-model="operaObjectType"
          class="ml-8"
          :desc="t('主机关联的所有实例一并替换')"
          icon="host"
          :title="t('整机替换')"
          :true-value="OperaObejctType.MACHINE" />
      </div>
    </div>
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <Component
        :is="comMap[operaObjectType]"
        :key="operaObjectType"
        ref="table"
        :ticket-details="ticketDetails" />
      <IgnoreBiz
        v-model="formData.force"
        v-bk-tooltips="t('如忽略_在有连接的情况下Proxy也会执行替换')" />
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';
  import { OperaObejctType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import InstanceReplace from './components/instance-replace/Index.vue';
  import MachineReplace from './components/machine-replace/Index.vue';

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const defaultData = () => ({
    force: false,
    payload: createTickePayload(),
  });

  const comMap = {
    [OperaObejctType.INSTANCE]: InstanceReplace,
    [OperaObejctType.MACHINE]: MachineReplace,
  };

  const operaObjectType = ref<keyof typeof comMap>(OperaObejctType.INSTANCE);
  const formData = reactive(defaultData());
  const ticketDetails = ref<Mysql.ResourcePool.ProxySwitch>();

  useTicketDetail<Mysql.ResourcePool.ProxySwitch>(TicketTypes.MYSQL_PROXY_SWITCH, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { force, opera_object: operaObject } = details;
      Object.assign(formData, {
        force,
        payload: createTickePayload(ticketDetail),
      });
      operaObjectType.value = operaObject;
      nextTick(() => {
        ticketDetails.value = details;
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    force: boolean;
    infos: {
      cluster_ids: number[];
      old_nodes: {
        origin_proxy: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          instance_address?: string;
          ip: string;
          port?: number;
        }[];
      };
      resource_spec: {
        target_proxy: {
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
        };
      };
    }[];
    ip_source: 'resource_pool';
    opera_object: OperaObejctType;
  }>(TicketTypes.MYSQL_PROXY_SWITCH);

  const handleSubmit = async () => {
    const infos = await tableRef.value!.getValue();
    if (infos.length) {
      createTicketRun({
        details: {
          force: formData.force,
          infos,
          ip_source: 'resource_pool',
          opera_object: operaObjectType.value,
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
