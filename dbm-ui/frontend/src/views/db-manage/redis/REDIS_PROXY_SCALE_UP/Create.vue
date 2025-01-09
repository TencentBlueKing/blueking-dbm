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
          :model="formData.tableData"
          :rules="rules">
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
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('扩容节点类型')"
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')"> Proxy </EditableBlock>
            </EditableColumn>
            <SpecSelectColumn
              v-model="item.spec_id"
              :current-spec-ids="getCurrentSpecIds(item.cluster.proxy)"
              field="spec_id"
              :label="t('扩容规格')"
              :params="{
                clusterType: ClusterTypes.REDIS,
                bkCloudId: item.cluster.bk_cloud_id,
                machineType: MachineTypes.REDIS_PROXY,
              }">
              <template #label="{ label, value }">
                {{ specLabelFormat({ label, value }, index) }}
              </template>
            </SpecSelectColumn>
            <EditableColumn
              field="target_proxy_count"
              :label="t('扩容数量（台）')"
              required
              :width="120">
              <EditableInput
                v-model="item.target_proxy_count"
                :min="1"
                :placeholder="t('不能少于n台', { n: 1 })"
                :rules="rules"
                type="number" />
            </EditableColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, MachineTypes, TicketTypes } from '@common/const';

  import { type TabConfig } from '@components/cluster-selector/Index.vue';

  import SpecSelectColumn from '@views/db-manage/common/toolbox-field/column/spec-select-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  interface IDataRow {
    cluster: {
      id: number;
      master_domain: string;
      cluster_type: string;
      cluster_type_name: string;
      bk_cloud_id: number;
      proxy: RedisModel['proxy'];
      cluster_spec: {
        id: number;
      };
    };
    spec_id: number;
    target_proxy_count: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
        cluster_type: '',
        cluster_type_name: '',
        bk_cloud_id: 0,
        proxy: [] as RedisModel['proxy'],
        cluster_spec: {
          id: 0,
        },
      },
      values.cluster,
    ),
    spec_id: values?.spec_id || 0,
    target_proxy_count: values?.target_proxy_count || 0,
  });

  const createDefaultFormData = () => ({
    tableData: [createRowData()],
    ...createTickePayload(),
  });

  const { t } = useI18n();

  useTicketDetail<Redis.ProxyScaleUp>(TicketTypes.REDIS_PROXY_SCALE_UP, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;
      Object.assign(formData, {
        tableData: infos.map((infoItem) => ({
          cluster: {
            master_domain: clusters[infoItem.cluster_id].immute_domain,
          },
          spec_id: infoItem.resource_spec.proxy.spec_id,
          target_proxy_count: infoItem.resource_spec.proxy.count,
        })),
        remark,
      });
      window.changeConfirm = true;
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    ip_source: 'resource_pool';
    infos: {
      cluster_id: number;
      bk_cloud_id: number;
      target_proxy_count: number;
      resource_spec: {
        proxy: {
          spec_id: number;
          count: number;
        };
      };
    }[];
  }>(TicketTypes.REDIS_PROXY_SCALE_UP);

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = formData.tableData.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
    target_proxy_count: [
      {
        validator: (value: number) => value >= 1,
        trigger: 'change',
        message: t('不能少于n台', { n: 1 }),
      },
    ],
  };

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
  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterColumn>['selected'] = {
      [ClusterTypes.REDIS]: [],
    };
    formData.tableData.forEach((tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id && masterDomain) {
        selectedClusters[ClusterTypes.REDIS].push({
          id,
          master_domain: masterDomain,
        });
      }
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const getCurrentSpecIds = (proxy: IDataRow['cluster']['proxy']) => {
    const specIdList = (proxy || []).map((proxyItem) => proxyItem.spec_config.id);
    return Array.from(new Set(specIdList));
  };

  const specLabelFormat = ({ value, label }: { value: number; label: string }, index: number) => {
    const row = formData.tableData[index];
    const specCount = row.cluster.proxy.filter((proxyItem) => proxyItem.spec_config.id === value).length;
    return specCount ? `${label} ${t('((n))台', { n: specCount })}` : label;
  };

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        const domain = item.master_domain;
        if (!clusterMemo.value[domain]) {
          newList.push(
            createRowData({
              cluster: {
                id: item.id,
                master_domain: item.master_domain,
                cluster_type: item.cluster_type,
                cluster_type_name: item.cluster_type_name,
                bk_cloud_id: item.bk_cloud_id,
                proxy: item.proxy,
                cluster_spec: item.cluster_spec,
              },
            }),
          );
        }
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          ip_source: 'resource_pool',
          infos: formData.tableData.map((tableItem) => ({
            cluster_id: tableItem.cluster.id,
            bk_cloud_id: tableItem.cluster.bk_cloud_id,
            target_proxy_count: tableItem.cluster.proxy.length + tableItem.target_proxy_count,
            resource_spec: {
              proxy: {
                spec_id: tableItem.spec_id,
                count: tableItem.target_proxy_count,
              },
            },
          })),
        },
        remark: formData.remark,
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
