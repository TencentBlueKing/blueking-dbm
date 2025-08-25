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
    <div class="version-upgrade-page">
      <BkAlert
        closable
        theme="info"
        :title="t('版本升级：将集群的接入层或存储层，更新到指定版本')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('角色类型')"
          property="nodeType"
          required>
          <BkRadioGroup v-model="formData.nodeType">
            <BkRadioButton
              :label="NodeType.PROXY"
              style="width: 180px">
              {{ t('接入层') }}
            </BkRadioButton>
            <BkRadioButton
              :label="NodeType.BACKEND"
              style="width: 180px">
              {{ t('存储层') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('升级类型')"
          property="updateType"
          required>
          <CardCheckbox
            v-model="formData.updateType"
            :desc="
              formData.nodeType === NodeType.PROXY
                ? t('选择目标集群后，该集群内所有接入层主机将同步升级')
                : t('选择目标集群，该集群内所有存储层主机（含主从）将同步升级')
            "
            icon="cluster"
            style="width: 450px"
            :title="t('指定集群升级')"
            :true-value="UpdateType.CLUSTER" />
          <CardCheckbox
            v-model="formData.updateType"
            class="ml-8"
            :desc="
              formData.nodeType === NodeType.PROXY
                ? t('直接选择单台或多台接入层主机，仅选中的主机独立升级')
                : t('选主节点时强制关联从节点升级；单选从节点则单独升级')
            "
            icon="host"
            style="width: 450px"
            :title="t('指定主机升级')"
            :true-value="UpdateType.MACHINE" />
        </BkFormItem>
        <component
          :is="currentTable"
          ref="currentTable"
          :node-type="formData.nodeType" />
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

  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import BackendCluster from './components/backend-cluster/Index.vue';
  import BackendMachine from './components/backend-machine/Index.vue';
  import ProxyCluster from './components/proxy-cluster/Index.vue';
  import ProxyMachine from './components/proxy-machine/Index.vue';

  const NodeType = {
    BACKEND: 'Backend',
    PROXY: 'Proxy',
  };

  const UpdateType = {
    CLUSTER: 'cluster',
    MACHINE: 'machine',
  };

  const createDefaultFormData = () => ({
    nodeType: NodeType.PROXY,
    payload: createTickePayload(),
    updateType: UpdateType.CLUSTER,
  });

  const { t } = useI18n();

  const currentTableRef = useTemplateRef('currentTable');

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos, update_type: updateType } = details;

      formData.nodeType = infos[0].node_type;
      formData.updateType = updateType;
      formData.payload = createTickePayload(ticketDetail);
      window.changeConfirm = true;
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      current_versions: string[];
      node_type: string;
      slave_current_versions: string[]; // 回显
      target_versions: {
        instance_role: string; // 回显
        ip: string;
        related_clusters: string[]; // 回显
        slave_ip: string; // 回显
        version: string;
      }[];
    }[];
    update_type: string;
  }>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE);

  const formData = reactive(createDefaultFormData());

  const currentTable = computed(() => {
    const key = `${formData.nodeType}_${formData.updateType}`;
    const componentMap = {
      [`${NodeType.BACKEND}_${UpdateType.CLUSTER}`]: BackendCluster,
      [`${NodeType.BACKEND}_${UpdateType.MACHINE}`]: BackendMachine,
      [`${NodeType.PROXY}_${UpdateType.CLUSTER}`]: ProxyCluster,
      [`${NodeType.PROXY}_${UpdateType.MACHINE}`]: ProxyMachine,
    };
    return componentMap[key];
  });

  const handleSubmit = async () => {
    const infos = await currentTableRef.value!.getValue();
    if (infos.length > 0) {
      createTicketRun({
        details: {
          infos,
          update_type: formData.updateType,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    currentTableRef.value!.resetTable();
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .version-upgrade-page {
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
