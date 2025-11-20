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
    <div>
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
        <BatchInput
          :config="batchInputConfig"
          @change="handleBatchInput" />
        <EditableTable
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <InstanceColumn
              ref="instanceColumnRef"
              v-model="item.batchInstance"
              :selected="selected"
              :selected-map="selectedMap"
              :tab-list-config="tabListConfig"
              @batch-edit="handleInstanceSelectChange" />
            <EditableColumn
              :append-rules="masterDomainRules"
              field="batchInstance.renderText"
              :label="t('所属集群')"
              :min-width="300"
              readonly
              :rowspan="item.rowspan">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                <div
                  v-for="domainItem in _.uniq(
                    Object.values(item.batchInstance.instances).map((item) => item.master_domain),
                  )"
                  :key="domainItem">
                  {{ domainItem }}
                </div>
              </EditableBlock>
            </EditableColumn>
            <SpecColumn
              v-model="item.batchInstance.current_spec_id"
              :cluster-type="DBTypes.REDIS"
              field="batchInstance.current_spec_id"
              label="规格" />
            <!-- <CurrentVersionColumn
              v-model="item.current_versions"
              :cluster-id="Object.values(item.batchInstance.instances)?.[0]?.cluster_id" /> -->
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

<script setup lang="tsx">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisClusterList, getRedisInstances } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import ManualInputHostContent from '@components/instance-selector/components/common/manual-content/Index.vue';
  import { type PanelListType } from '@components/instance-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import MigrateFormItems, {
    ArchitectureType,
    MigrateType,
  } from '@views/db-manage/redis/common/toolbox-common/migrate-form-items/Index.vue';

  // import CurrentVersionColumn from './components/CurrentVersionColumn.vue';
  import InstanceColumn from './components/InstanceColumn.vue';

  interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  interface IDataRow {
    batchInstance: ComponentProps<typeof InstanceColumn>['modelValue'];
    current_versions: string[];
    rowspan: number;
  }

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');
  const instanceColumnRef = useTemplateRef<Array<InstanceType<typeof InstanceColumn>>>('instanceColumnRef');

  const batchInputConfig = [
    {
      case: '192.168.10.2:10000\\n192.168.10.2:10001',
      key: 'instance',
      label: t('目标实例'),
    },
  ];

  // 单据克隆
  useTicketDetail<Redis.MigrateCluster>(TicketTypes.REDIS_CLUSTER_INS_MIGRATE, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            batchInstance: {
              renderText: infoItem.migrate_instance,
            } as IDataRow['batchInstance'],
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{ infos: Redis.MigrateCluster['infos'] }>(
    TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
  );

  const initFormData = () => ({
    architectureType: ArchitectureType.CLUSTER,
    migrateType: MigrateType.INSTANCE,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    batchInstance: Object.assign(
      {
        current_spec_id: 0,
        instances: {} as IDataRow['batchInstance']['instances'],
        renderText: '',
      },
      values.batchInstance,
    ),
    current_versions: values?.current_versions || [],
    rowspan: values?.rowspan || 1,
  });

  const masterDomainRules = [
    {
      message: t('目前只支持 Tendiscahce 和 Tendisssd 集群'),
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IDataRow }) =>
        ![ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER].includes(
          Object.values(rowData.batchInstance.instances)?.[0]!.cluster_type as ClusterTypes,
        ),
    },
  ];

  const formData = reactive(initFormData());

  const tabListConfig = computed(
    () =>
      ({
        RedisInstance: [
          {
            name: t('实例选择'),
            tableConfig: {
              firsrColumn: {
                field: 'instance_address',
                label: t('Master 实例'),
                role: '',
              },
              getTableList: (params: ServiceParameters<typeof getRedisInstances>) =>
                getRedisInstances({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    // ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    // ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  role: 'redis_master',
                  ...params,
                }),
              multiple: true,
            },
            topoConfig: {
              countFunc: (data: RedisModel) => data.redis_master.length,
              getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
                getRedisClusterList({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    // ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    // ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  ...params,
                }),
              totalCountFunc: (dataList: RedisModel[]) =>
                dataList.reduce<number>((prevCount, item) => prevCount + item.redis_master.length, 0),
            },
          },
          {
            content: ManualInputHostContent,
            manualConfig: {
              fieldFormat: {
                role: {
                  master: 'redis_master',
                },
              },
            },
            tableConfig: {
              firsrColumn: {
                field: 'instance_address',
                label: t('Master 实例'),
                role: 'redis_master',
              },
              getTableList: (params: ServiceParameters<typeof getRedisInstances>) =>
                getRedisInstances({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    // ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    // ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  ...params,
                }),
              multiple: true,
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  const selected = computed(() =>
    formData.tableData
      .filter((item) => item.batchInstance.renderText)
      .flatMap((item) => Object.values(item.batchInstance.instances)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  // 批量选择
  const handleInstanceSelectChange = (data: RedisInstanceModel[]) => {
    const newList: IDataRow[] = [];
    data.forEach((item) => {
      const { instance_address: instance } = item;
      if (!selectedMap.value[instance]) {
        newList.push(
          createRowData({
            batchInstance: {
              renderText: item.instance_address,
            } as IDataRow['batchInstance'],
          }),
        );
      }
    });

    formData.tableData = [...formData.tableData.filter((item) => item.batchInstance.renderText), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          batchInstance: {
            renderText: item.instance?.replaceAll('\\n', '\n') || '',
          } as IDataRow['batchInstance'],
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      formData.tableData = [...newList];
    } else {
      formData.tableData = [...formData.tableData.filter((item) => item.batchInstance.renderText), ...newList];
    }
    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => {
            const instances = Object.values(tableItem.batchInstance.instances);
            const oldNodes = instances.reduce<{
              master: IHostData[];
              slave: IHostData[];
            }>(
              (prev, item) => {
                return Object.assign(prev, {
                  master: prev.master.concat({
                    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                    bk_cloud_id: item.bk_cloud_id,
                    bk_host_id: item.bk_host_id,
                    ip: item.ip,
                    port: item.port,
                  }),
                  slave: prev.slave.concat(item.slave),
                });
              },
              {
                master: [],
                slave: [],
              },
            );
            const [instance] = instances;
            return {
              cluster_id: instance!.cluster_id,
              db_version: tableItem.current_versions,
              migrate_instance: instances.map((item) => item.instance_address).join(','),
              // old_nodes: oldNodes,
              origin_old_nodes: oldNodes,
              resource_spec: {
                backend_group: {
                  count: 1,
                  spec_id: instance!.spec_config.id,
                },
              },
            };
          }),
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, initFormData());
    window.changeConfirm = false;
  };
</script>
