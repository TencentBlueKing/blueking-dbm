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
  <SmartAction class="redis-proxy-fast-fix">
    <BkAlert
      class="mb-20"
      closable
      :title="t('用于批量执行剔除异常 Proxy，或将剔除的 Proxy 加回集群')" />
    <DbForm
      class="toolbox-form mb-16"
      form-type="vertical"
      :model="formData">
      <DbFormItem
        :label="t('操作类型')"
        property="ticketType"
        required>
        <CardCheckbox
          v-model="formData.ticketType"
          :desc="t('将 Proxy 从集群中剔除，该 Proxy 不再提供服务')"
          icon="minus-fill"
          :title="t('Proxy 剔除')"
          :true-value="TicketTypes.REDIS_PROXY_KICKOFF" />
        <CardCheckbox
          v-model="formData.ticketType"
          class="ml-8"
          :desc="t('将剔除的 Proxy 重新加回集群，该 Proxy 恢复提供服务')"
          icon="plus-fill"
          :title="t('Proxy 修复')"
          :true-value="TicketTypes.REDIS_PROXY_FIX" />
      </DbFormItem>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.proxy"
            :selected="selected"
            @batch-edit="handleHostBatchEdit" />
          <EditableColumn
            :label="t('地域')"
            :min-width="120"
            readonly>
            <EditableBlock
              v-model="item.proxy.city_name"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('园区')"
            :min-width="120"
            readonly>
            <EditableBlock
              v-model="item.proxy.bk_sub_zone"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('关联集群')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.proxy.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
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
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';
  import { type IValue } from '@components/instance-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import HostColumn from './components/HostColumn.vue';

  interface IDataRow {
    proxy: ComponentProps<typeof HostColumn>['modelValue'];
  }

  const { t } = useI18n();
  const router = useRouter();

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('Proxy 主机'),
    },
  ];

  useTicketDetail<Redis.ProxyFix>(TicketTypes.REDIS_PROXY_FIX, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.flatMap((infoItem) =>
          infoItem.proxy.map((item) =>
            createTableRow({
              proxy: {
                ip: item.ip,
              } as IDataRow['proxy'],
            }),
          ),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Redis.ProxyFix['infos'];
  }>(TicketTypes.REDIS_PROXY_FIX);

  const createTableRow = (values: DeepPartial<IDataRow> = {}) => ({
    proxy: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_sub_zone: '',
        city_name: '',
        cluster_id: 0,
        cluster_type: '',
        ip: '',
        master_domain: '',
        role: '',
      },
      values.proxy,
    ),
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
    ticketType: TicketTypes.REDIS_PROXY_FIX,
  });

  const tableRef = useTemplateRef('table');
  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.proxy.bk_host_id).map((item) => item.proxy));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  watch(
    () => formData.ticketType,
    () => {
      if (formData.ticketType === TicketTypes.REDIS_PROXY_KICKOFF)
        router.push({
          name: TicketTypes.REDIS_PROXY_KICKOFF,
        });
    },
  );

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }

    const sameClusters = _.groupBy(formData.tableData, (item) => item.proxy.master_domain);

    const infos = Object.values(sameClusters).map((sameRows) => {
      const proxy = sameRows.map((row) => ({
        bk_cloud_id: row.proxy.bk_cloud_id,
        bk_host_id: row.proxy.bk_host_id,
        bk_sub_zone: row.proxy.bk_sub_zone,
        city: row.proxy.city_name,
        ip: row.proxy.ip,
      }));
      return {
        cluster_id: sameRows[0].proxy.cluster_id,
        operate_type: 'PROXY_ENTRY_FIX' as const,
        proxy,
        restart_proxy: false,
      };
    });

    createTicketRun({
      details: {
        infos,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleHostBatchEdit = (list: IValue[]) => {
    const dataList = list.reduce<IDataRow[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            proxy: {
              ip: item.ip,
            } as IDataRow['proxy'],
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].proxy.bk_host_id ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createTableRow({
          proxy: {
            ip: item.ip,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].proxy.bk_host_id ? formData.tableData : []), ...dataList];
    }
  };
</script>
