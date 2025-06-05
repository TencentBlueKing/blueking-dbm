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
    <div class="proxy-scale-up-page">
      <BkAlert
        closable
        theme="info"
        :title="t('扩容接入层：增加集群的Proxy数量，新Proxy可以指定规格')" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.REDIS]"
              field="cluster.master_domain"
              :label="t('目标集群')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('架构版本')"
              :width="180">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('扩容节点类型')"
              :width="120">
              <EditableBlock :placeholder="t('选择集群后自动生成')"> Proxy </EditableBlock>
            </EditableColumn>
            <SpecSelectColumn
              v-model="item.spec_id"
              :bk-cloud-id="item.cluster.bk_cloud_id"
              :cluster-type="ClusterTypes.REDIS"
              :current-spec-ids="getCurrentSpecIds(item.cluster.proxy)"
              field="spec_id"
              :label="t('扩容规格')"
              :machine-type="MachineTypes.REDIS_PROXY">
              <template #label="{ label, value }">
                {{ specLabelFormat({ label, value }, index) }}
              </template>
            </SpecSelectColumn>
            <TargetProxyCountColumn
              v-model="item.target_proxy_count"
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, MachineTypes, TicketTypes } from '@common/const';

  import { type TabConfig } from '@components/cluster-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import SpecSelectColumn from '@views/db-manage/redis/common/toolbox-field/spec-select-column/Index.vue';

  import TargetProxyCountColumn from './components/TargetProxyCountColumn.vue';

  interface IDataRow {
    cluster: {
      bk_cloud_id: number;
      cluster_spec: {
        id: number;
      };
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      proxy: RedisModel['proxy'];
    };
    spec_id: number;
    target_proxy_count: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_spec: {
          id: 0,
        },
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        proxy: [] as RedisModel['proxy'],
      },
      values.cluster,
    ),
    spec_id: values?.spec_id || 0,
    target_proxy_count: values?.target_proxy_count || '',
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Redis.ProxyScaleUp>(TicketTypes.REDIS_PROXY_SCALE_UP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            spec_id: infoItem.resource_spec.proxy.spec_id,
            target_proxy_count: String(infoItem.resource_spec.proxy.count),
          }),
        ),
      });
      window.changeConfirm = true;
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      bk_cloud_id: number;
      cluster_id: number;
      resource_spec: {
        proxy: {
          count: number;
          spec_id: number;
        };
      };
      target_proxy_count: number;
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_PROXY_SCALE_UP);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
    },
  } as unknown as Record<string, TabConfig>;

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const getCurrentSpecIds = (proxy: IDataRow['cluster']['proxy']) => {
    const specIdList = (proxy || []).map((proxyItem) => proxyItem.spec_config.id);
    return Array.from(new Set(specIdList));
  };

  const specLabelFormat = ({ label, value }: { label: string; value: number }, index: number) => {
    const row = formData.tableData[index];
    const specCount = row.cluster.proxy.filter((proxyItem) => proxyItem.spec_config.id === value).length;
    return specCount ? `${label} ${t('((n))台', { n: specCount })}` : label;
  };

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_spec: item.cluster_spec,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
              proxy: item.proxy,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            bk_cloud_id: tableItem.cluster.bk_cloud_id,
            cluster_id: tableItem.cluster.id,
            resource_spec: {
              proxy: {
                count: Number(tableItem.target_proxy_count),
                spec_id: tableItem.spec_id,
              },
            },
            target_proxy_count: tableItem.cluster.proxy.length + Number(tableItem.target_proxy_count),
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-up-page {
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

  .bottom-btn {
    width: 88px;
  }
</style>
