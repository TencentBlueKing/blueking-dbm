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
    <div class="mb-24">
      <RenderTable>
        <template #default>
          <RenderTableHeadColumn
            fixed="left"
            :width="200">
            <span>{{ t('目标 Master 实例') }}</span>
            <template #append>
              <BatchOperateIcon
                class="ml-4"
                @click="handleShowMasterBatchSelector" />
            </template>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :required="false"
            :width="220">
            <span>{{ t('所属集群') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :required="false"
            :width="220">
            <span>{{ t('规格') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :required="false"
            :width="220">
            <span>{{ t('版本') }}</span>
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            fixed="right"
            :required="false"
            :width="100">
            {{ t('操作') }}
          </RenderTableHeadColumn>
        </template>
        <template #data>
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :removeable="tableData.length < 2"
            @add="(payload) => handleAppend(index, payload)"
            @clone="(payload) => handleClone(index, payload)"
            @input-finish="(value) => handleChangeCluster(index, value)"
            @remove="handleRemove(index)" />
        </template>
      </RenderTable>
      <TicketRemark v-model="localRemark" />
      <InstanceSelector
        v-model:is-show="isShowInstaceSelector"
        :cluster-types="[ClusterTypes.REDIS]"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @change="handleInstanceSelectChange" />
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
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { getRedisClusterList, getRedisInstances } from '@services/source/redis';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';
  import { createTicket } from '@services/source/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ManualInputHostContent from '@components/instance-selector/components/common/manual-content/Index.vue';
  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import BatchOperateIcon from '@views/db-manage/common/batch-operate-icon/Index.vue';

  import { random } from '@utils';

  import RenderDataRow, { createRowData, type IDataRow, type IHostData } from './Row.vue';

  interface Props {
    tableList: IDataRow[];
    remark: string;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();

  const tableData = ref([createRowData()]);
  const isShowInstaceSelector = ref(false);
  const rowRefs = ref();
  const isSubmitting = ref(false);
  const localRemark = ref('');

  const selected = shallowRef({ [ClusterTypes.REDIS]: [] } as InstanceSelectorValues<RedisInstanceModel>);

  const selectedClusters = shallowRef<{ [key: string]: RedisInstanceModel[] }>({ [ClusterTypes.REDIS]: [] });

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.REDIS]: [
          {
            name: t('实例选择'),
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
                getRedisClusterList({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  ...params,
                }),
              countFunc: (data: RedisModel) => data.redis_master.length,
              totalCountFunc: (dataList: RedisModel[]) =>
                dataList.reduce<number>((prevCount, item) => prevCount + item.redis_master.length, 0),
            },
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getRedisInstances>) =>
                getRedisInstances({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  role: 'redis_master',
                  ...params,
                }),
              multiple: true,
              firsrColumn: {
                label: t('Master 实例'),
                field: 'instance_address',
                role: '',
              },
              columnsChecked: ['instance_address', 'cloud_area', 'status', 'host_name', 'os_name'],
            },
            previewConfig: {
              displayKey: 'instance_address',
            },
          },
          {
            manualConfig: {
              checkType: 'instance',
              checkKey: 'instance_address',
              activePanelId: 'redis',
              fieldFormat: {
                role: {
                  master: 'redis_master',
                },
              },
            },
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getRedisInstances>) =>
                getRedisInstances({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  ...params,
                }),
              firsrColumn: {
                label: t('Master 实例'),
                field: 'instance_address',
                role: 'redis_master',
              },
              multiple: true,
            },
            previewConfig: {
              displayKey: 'instance_address',
            },
            content: ManualInputHostContent,
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  watch(
    () => props.tableList,
    () => {
      nextTick(() => {
        tableData.value = props.tableList.length > 0 ? props.tableList : [createRowData()];
        sortTableByCluster();
      });
    },
    {
      immediate: true,
    },
  );

  watchEffect(() => {
    localRemark.value = props.remark;
  });

  // 集群实例是否已存在表格的映射表
  let instanceMemo: Record<string, boolean> = {};

  const handleShowMasterBatchSelector = () => {
    isShowInstaceSelector.value = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
    sortTableByCluster();
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    if (removeItem.clusterData) {
      const { domain } = removeItem.clusterData;
      delete instanceMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.REDIS];
      selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter((item) => item.master_domain !== domain);
    }
    tableData.value.splice(index, 1);
    sortTableByCluster();
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    tableData.value.splice(index + 1, 0, sourceData);
    sortTableByCluster();
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  // 表格排序，方便合并集群显示
  const sortTableByCluster = () => {
    const clusterMap = {} as Record<string, IDataRow[]>;
    const emptyRows: IDataRow[] = [];
    tableData.value.forEach((item) => {
      if (item.clusterData) {
        const { domain } = item.clusterData;
        if (clusterMap[domain]) {
          clusterMap[domain].push(item);
        } else {
          clusterMap[domain] = [item];
        }
      } else {
        emptyRows.push(item);
      }
    });

    const spanRows = Object.values(clusterMap).flatMap((sameArr) => {
      const isGeneral = sameArr.length <= 1;
      return sameArr.map<IDataRow>((item, index) => ({
        ...item,
        spanData: {
          isStart: index === 0,
          rowSpan: index === 0 ? sameArr.length : 1,
          isGeneral,
        },
      }));
    });
    tableData.value = [...spanRows, ...emptyRows];
  };

  const generateTableRow = (item: RedisInstanceModel, master?: IHostData, slave?: IHostData) => ({
    rowKey: random(),
    isLoading: false,
    spanData: {
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
    clusterData: {
      instance: item.instance_address,
      domain: item.master_domain,
      clusterId: item.cluster_id,
      clusterType: item.cluster_type,
      specId: item.spec_config.id,
      specName: item.spec_config.name,
    },
    master,
    slave,
  });

  // 批量选择
  const handleInstanceSelectChange = async (data: InstanceSelectorValues<RedisInstanceModel>) => {
    selected.value = data;
    const newList: IDataRow[] = [];

    const slaveInstanceMap = await queryMachineInstancePair({
      instances: data[ClusterTypes.REDIS].map((item) => item.instance_address),
    });

    if (slaveInstanceMap && slaveInstanceMap.instances) {
      const masterInstanceMap = data[ClusterTypes.REDIS].reduce<
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
      Object.keys(masterInstanceMap).forEach((masterInstance) => {
        const slaveItem = slaveInstanceMap.instances![masterInstance];
        masterInstanceMap[masterInstance].slave = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: slaveItem.bk_cloud_id,
          bk_host_id: slaveItem.bk_host_id,
          ip: slaveItem.ip,
          port: slaveItem.port,
        };
      });

      data[ClusterTypes.REDIS].forEach((item) => {
        const { instance_address: instance } = item;
        if (!instanceMemo[instance]) {
          const masterSlave = masterInstanceMap[item.instance_address];
          newList.push(generateTableRow(item, masterSlave.master, masterSlave.slave));
          instanceMemo[instance] = true;
        }
      });
      if (checkListEmpty(tableData.value)) {
        tableData.value = newList;
      } else {
        tableData.value = [...tableData.value, ...newList];
      }
      sortTableByCluster();
      window.changeConfirm = true;
    }
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, value: string) => {
    tableData.value[index].isLoading = true;
    const result = await getRedisInstances({ instance_address: value }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length > 0) {
      const item = result.results[0];
      const row = generateTableRow(item);
      const newInstanceMap = await queryMachineInstancePair({
        instances: [value],
      });

      if (newInstanceMap && newInstanceMap.instances) {
        const slaveItem = newInstanceMap.instances[value];
        Object.assign(row, {
          master: {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            ip: item.ip,
            port: item.port,
          },
          slave: {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: slaveItem.bk_cloud_id,
            bk_host_id: slaveItem.bk_host_id,
            ip: slaveItem.ip,
            port: slaveItem.port,
          },
        });
      }

      tableData.value[index] = row;
      instanceMemo[item.instance_address] = true;
      selectedClusters.value[ClusterTypes.REDIS].push(item);
    }
    sortTableByCluster();
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow?.clusterData;
  };

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
      await createTicket({
        ticket_type: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
        remark: localRemark.value,
        details: {
          infos,
        },
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'RedisMigrate',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    localRemark.value = '';
    instanceMemo = {};
    selectedClusters.value[ClusterTypes.REDIS] = [];
    window.changeConfirm = false;
  };
</script>
