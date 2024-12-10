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
      <strong class="proxy-switch-types-title">
        {{ t('替换类型') }}
      </strong>
      <div class="mt-8 mb-20">
        <CardCheckbox
          v-model="replaceType"
          :desc="t('只替换目标实例')"
          icon="rebuild"
          :title="t('实例替换')"
          :true-value="ProxyReplaceTypes.INSTANCE_REPLACE" />
        <CardCheckbox
          v-model="replaceType"
          class="ml-8"
          :desc="t('主机关联的所有实例一并替换')"
          icon="host"
          :title="t('整机替换')"
          :true-value="ProxyReplaceTypes.HOST_REPLACE" />
      </div>
    </div>
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <Component
        :is="tableComponentMap[replaceType]"
        ref="table"
        :data="formData.tableData" />
      <IgnoreBiz
        v-model="formData.force"
        v-bk-tooltips="t('如忽略_在有连接的情况下Proxy也会执行替换')" />
      <TicketRemark v-model="formData.remark" />
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

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import HostTable from './components/HostTable.vue';
  import InstanceTable from './components/InstanceTable.vue';
  import { ProxyReplaceTypes } from './types';

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const defaultData = () => ({
    tableData: [],
    force: false,
    remark: '',
  });

  const tableComponentMap = {
    [ProxyReplaceTypes.INSTANCE_REPLACE]: InstanceTable,
    [ProxyReplaceTypes.HOST_REPLACE]: HostTable,
  };

  const replaceType = ref(ProxyReplaceTypes.INSTANCE_REPLACE);
  const formData = reactive(defaultData());

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    force: boolean;
    infos: {
      cluster_ids: number[];
      origin_proxy: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port?: number;
        instance_address?: string;
      };
      target_proxy: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      display_info: {
        type: ProxyReplaceTypes;
        related_clusters: string[];
      };
    }[];
  }>(TicketTypes.MYSQL_PROXY_SWITCH);

  const handleSubmit = async () => {
    const infos = await tableRef.value!.getValue();
    if (infos.length) {
      createTicketRun({
        details: {
          force: formData.force,
          infos,
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
  .proxy-switch-types-title {
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

  .safe-action-text {
    padding-bottom: 2px;
    border-bottom: 1px dashed #979ba5;
  }
</style>
