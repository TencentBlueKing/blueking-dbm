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
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <InstanceColumn
              ref="instanceColumnRef"
              v-model="item.instance"
              :after-input="(data: InstanceInfos) => afterInput(data, index)"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleInstanceSelectChange" />
            <EditableColumn
              :append-rules="masterDomainRules"
              field="instance.master_domain"
              :label="t('所属集群')"
              :min-width="300"
              :rowspan="item.rowspan">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                {{ item.instance.master_domain }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('规格')"
              :width="200">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                {{ item.instance.spec_config.id ? item.instance.spec_config.name : '' }}
              </EditableBlock>
            </EditableColumn>
            <CurrentVersionColumn
              v-model="item.current_versions"
              :cluster-id="item.instance.cluster_id" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisClusterList, getRedisInstances } from '@services/source/redis';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';
  import type { InstanceInfos } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ManualInputHostContent from '@components/instance-selector/components/common/manual-content/Index.vue';
  import { type PanelListType } from '@components/instance-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import MigrateFormItems, {
    ArchitectureType,
    MigrateType,
  } from '@views/db-manage/redis/common/toolbox-field/migrate-form-items/Index.vue';

  import CurrentVersionColumn from './components/CurrentVersionColumn.vue';
  import InstanceColumn from './components/InstanceColumn.vue';

  interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  interface IDataRow {
    current_versions: string[];
    instance: {
      bk_host_id: number;
      cluster_id: number;
      cluster_type: string;
      instance_address: string;
      master_domain: string;
      spec_config: RedisInstanceModel['spec_config'];
    };
    master: IHostData;
    rowspan: number;
    slave: IHostData;
  }

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');
  const instanceColumnRef = useTemplateRef<Array<InstanceType<typeof InstanceColumn>>>('instanceColumnRef');

  // 单据克隆
  useTicketDetail<Redis.MigrateCluster>(TicketTypes.REDIS_CLUSTER_INS_MIGRATE, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            instance: {
              instance_address: infoItem.display_info.instance,
            } as IDataRow['instance'],
          }),
        ),
      });
      nextTick(() => {
        instanceColumnRef.value!.map((item) => item.inputManualChange());
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      display_info: {
        db_version: string[];
        instance: string;
      };
      old_nodes: {
        master: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
        slave: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        }[];
      };
      resource_spec: {
        backend_group: {
          count: number;
          spec_id: number;
        };
      };
    }[];
  }>(TicketTypes.REDIS_CLUSTER_INS_MIGRATE);

  const initFormData = () => ({
    architectureType: ArchitectureType.CLUSTER,
    migrateType: MigrateType.INSTANCE,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    current_versions: values?.current_versions || [],
    instance: Object.assign(
      {
        bk_host_id: 0,
        cluster_id: 0,
        cluster_type: '',
        instance_address: '',
        master_domain: '',
        spec_config: {} as RedisInstanceModel['spec_config'],
      },
      values.instance,
    ),
    master: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
      },
      values.master,
    ),
    rowspan: values?.rowspan || 1,
    slave: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
      },
      values.slave,
    ),
  });

  const masterDomainRules = [
    {
      message: t('目前只支持 Tendiscahce 和 Tendisssd 集群'),
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IDataRow }) =>
        ![ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER].includes(
          rowData.instance.cluster_type as ClusterTypes,
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
    formData.tableData.filter((item) => item.instance.bk_host_id).map((item) => item.instance),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  const getMasterSlaveInstaceMap = async (
    data: {
      bk_cloud_id: number;
      bk_host_id: number;
      instance_address: string;
      ip: string;
      port: number;
    }[],
  ) => {
    const slaveInstanceMap = await queryMachineInstancePair({
      instances: data.map((item) => item.instance_address),
    });

    if (slaveInstanceMap && slaveInstanceMap.instances) {
      const masterSlaveInstaceMap = data.reduce<
        Record<
          string,
          {
            master: IHostData;
            slave: IHostData;
          }
        >
      >(
        (prevMap, instanceItem) =>
          Object.assign({}, prevMap, {
            [instanceItem.instance_address]: {
              master: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: instanceItem.bk_cloud_id,
                bk_host_id: instanceItem.bk_host_id,
                ip: instanceItem.ip,
                port: instanceItem.port,
              },
            },
          }),
        {},
      );
      Object.keys(masterSlaveInstaceMap).forEach((masterInstance) => {
        const slaveItem = slaveInstanceMap.instances![masterInstance];
        masterSlaveInstaceMap[masterInstance].slave = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: slaveItem.bk_cloud_id,
          bk_host_id: slaveItem.bk_host_id,
          ip: slaveItem.ip,
          port: slaveItem.port,
        };
      });

      return masterSlaveInstaceMap;
    }

    return {};
  };

  // 批量选择
  const handleInstanceSelectChange = async (data: RedisInstanceModel[]) => {
    const newList: IDataRow[] = [];
    const masterSlaveInstaceMap = await getMasterSlaveInstaceMap(data);
    data.forEach((item) => {
      const { instance_address: instance } = item;
      if (!selectedMap.value[instance]) {
        const { slave } = masterSlaveInstaceMap[item.instance_address];
        newList.push(
          createRowData({
            instance: {
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              cluster_type: item.cluster_type,
              instance_address: item.instance_address,
              master_domain: item.master_domain,
              spec_config: item.spec_config,
            },
            master: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              port: item.port,
            },
            slave: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: slave.bk_cloud_id,
              bk_host_id: slave.bk_host_id,
              ip: slave.ip,
              port: slave.port,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;

    nextTick(() => {
      editableTableRef.value!.validateByField('instance.master_domain');
    });
  };

  const afterInput = async (data: InstanceInfos, index: number) => {
    const masterSlaveInstaceMap = await getMasterSlaveInstaceMap([data]);
    // const { instance_address: instance } = data;
    // if (!selectedMap.value[instance]) {
    const { slave } = masterSlaveInstaceMap[data.instance_address];
    formData.tableData[index] = createRowData({
      instance: {
        bk_host_id: data.bk_host_id,
        cluster_id: data.cluster_id,
        cluster_type: data.cluster_type,
        instance_address: data.instance_address,
        master_domain: data.master_domain,
        spec_config: data.spec_config,
      },
      master: {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: data.bk_cloud_id,
        bk_host_id: data.bk_host_id,
        ip: data.ip,
        port: data.port,
      },
      slave: {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: slave.bk_cloud_id,
        bk_host_id: slave.bk_host_id,
        ip: slave.ip,
        port: slave.port,
      },
    });
    // }

    nextTick(() => {
      editableTableRef.value!.validateByField('instance.master_domain');
    });
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            cluster_id: tableItem.instance.cluster_id,
            display_info: {
              db_version: tableItem.current_versions,
              instance: tableItem.instance.instance_address,
            },
            old_nodes: {
              master: [tableItem.master],
              slave: [tableItem.slave],
            },
            resource_spec: {
              backend_group: {
                count: 1,
                spec_id: tableItem.instance.spec_config.id,
              },
            },
          })),
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
