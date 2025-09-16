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
  <EditableColumn
    :disabled-method="disabledMethod"
    field="scope"
    :label="t('校验范围')"
    :min-width="120"
    required
    :rowspan="rowspan">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="scopeOptions"
        :title="t('校验范围')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="scope"
      :list="scopeOptions"
      @change="handleChangeScope">
    </EditableSelect>
  </EditableColumn>
  <EditableColumn
    ref="column"
    :disabled-method="disabledMethod"
    field="slaves"
    :label="t('校验从库')"
    :min-width="180"
    :readonly="scope === 'all'"
    :required="scope !== 'all'">
    <EditableBlock>
      <div
        v-if="slaves.length === 0 && scope !== 'all'"
        class="tendbcluster-checksum-slave-default"
        @click="handleShowSelector">
        <div class="tendbcluster-checksum-placeholder">
          {{ t('请选择') }}
        </div>
        <DbIcon
          class="angle-down render-slaves-icon"
          size="small"
          type="bk-dbm-icon db-icon-down-big" />
      </div>

      <div v-if="scope === 'all'">{{ t('全部') }}</div>
      <div
        v-else
        class="tendbcluster-checksum-slave-selected"
        @click="handleShowSelector">
        <p
          v-for="instance in slaves"
          :key="instance.instance_address">
          {{ instance.instance_address }}
        </p>
        <DbIcon
          class="edit-btn"
          type="edit" />
      </div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="master.instance_address"
    :label="t('校验主库')"
    :min-width="180"
    readonly
    :required="scope !== 'all'">
    <EditableBlock :placeholder="t('自动生成')">
      <div v-if="scope === 'all'">
        {{ t('全部') }}
      </div>
      <div v-else>
        {{ master.instance_address }}
      </div>
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="isShowInstanceSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selectorSelected"
    :tab-list-config="tabListConfig"
    @change="handleChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface InstanceInfo {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    instance_address: string;
    ip: string;
    port: number;
  }

  interface RowData {
    cluster: TendbClusterModel;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    master: typeof master.value;
    rowspan: number;
    scope: string;
    slaves: typeof slaves.value;
    table_patterns: string[];
  }

  interface Props {
    cluster: TendbClusterModel;
    createTableRow: (data: Partial<RowData>) => RowData;
    handleRowMerge: () => void;
    rowspan: number;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const scope = defineModel<string>('scope', {
    required: true,
  });

  const slaves = defineModel<InstanceInfo[]>('slaves', {
    required: true,
  });

  const master = defineModel<InstanceInfo>('master', {
    required: true,
  });

  const tableData = defineModel<RowData[]>('tableData', {
    required: true,
  });

  const { t } = useI18n();
  const columnRef = useTemplateRef('column');

  const selected = ref<string[]>([]);
  const selectorSelected = ref<InstanceSelectorValues<IValue>>({
    [ClusterTypes.TENDBCLUSTER]: [],
  });
  const isShowInstanceSelector = ref(false);
  const showBatchEdit = ref(false);

  const scopeOptions = [
    {
      label: t('整个集群'),
      value: 'all',
    },
    {
      label: t('部分实例'),
      value: 'partial',
    },
  ];

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.TENDBCLUSTER]: [
          {
            name: t('从库'),
            tableConfig: {
              firsrColumn: {
                field: 'instance_address',
                label: 'slave',
                role: 'backend_slave,backend_repeater,remote_slave,remote_repeater',
              },
              roleFilterList: {
                list: [
                  {
                    text: 'backend_slave',
                    value: 'backend_slave',
                  },
                  {
                    text: 'backend_repeater',
                    value: 'backend_repeater',
                  },
                  {
                    text: 'remote_slave',
                    value: 'remote_slave',
                  },
                  {
                    text: 'remote_repeater',
                    value: 'remote_repeater',
                  },
                ],
              },
            },
            topoConfig: {
              filterClusterId: props.cluster.id,
            },
          },
          {
            id: 'manualInput',
            name: t('手动输入'),
            tableConfig: {
              firsrColumn: {
                field: 'instance_address',
                label: 'slave',
                role: 'backend_slave,backend_repeater,remote_slave,remote_repeater',
              },
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    emits('batch-edit', value, 'scope');
  };

  const handleShowSelector = () => {
    isShowInstanceSelector.value = true;
  };

  const handleChange = async (payload: InstanceSelectorValues<IValue>) => {
    const selectedInstances = payload[ClusterTypes.TENDBCLUSTER];

    if (!selectedInstances.length) {
      slaves.value = [];
      master.value = {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        instance_address: '',
        ip: '',
        port: 0,
      };
      return;
    }

    // 选中的从库信息, instance -> slave info
    const slaveInfo = selectedInstances.reduce<Record<string, TendbclusterInstanceModel>>((acc, item) => {
      Object.assign(acc, {
        [item.instance_address]: item,
      });
      return acc;
    }, {});

    // 获取主从实例对信息
    const { instances } = await getRemoteMachineInstancePair({
      bk_biz_id: props.cluster.bk_biz_id,
      instances: selectedInstances.map((item) => item.instance_address),
    });

    // 主库信息, instance -> master info
    const masterInfo: Record<string, ServiceReturnType<typeof getRemoteMachineInstancePair>['instances'][string]> = {};
    // 按主库分组, master -> [slave, slave, ...]
    const groupByMaster: Record<string, string[]> = {};
    Object.entries(instances).forEach(([slave, master]) => {
      if (!masterInfo[master.instance]) {
        masterInfo[master.instance] = master;
      }
      if (!groupByMaster[master.instance]) {
        groupByMaster[master.instance] = [];
      }
      groupByMaster[master.instance].push(slave);
    });

    const list = Object.values(masterInfo).map((master) =>
      props.createTableRow({
        cluster: props.cluster,
        master: {
          bk_biz_id: master.bk_biz_id,
          bk_cloud_id: master.bk_cloud_id,
          bk_host_id: master.bk_host_id,
          instance_address: master.instance,
          ip: master.ip,
          port: master.port,
        },
        scope: 'partial',
        slaves: groupByMaster[master.instance].map((slave) => {
          const info = slaveInfo[slave];
          return {
            bk_biz_id: info.bk_biz_id,
            bk_cloud_id: info.bk_cloud_id,
            bk_host_id: info.bk_host_id,
            instance_address: info.instance_address,
            ip: info.ip,
            port: info.port,
          };
        }),
      }),
    );

    const rowIndex = columnRef.value!.getRowIndex();

    tableData.value.splice(rowIndex, 1, ...list);

    // 触发行合并
    setTimeout(() => {
      props.handleRowMerge();
    });
  };

  const handleChangeScope = (value: string) => {
    if (value === 'all') {
      const rowIndex = columnRef.value!.getRowIndex();
      const rowspan = tableData.value[rowIndex]?.rowspan;
      if (rowspan) {
        tableData.value[rowIndex].rowspan = 1;
        tableData.value.splice(rowIndex + 1, rowspan - 1);
      }
    }
    selected.value = [];
    slaves.value = [];
    master.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      instance_address: '',
      ip: '',
      port: 0,
    };
  };

  watch(
    slaves,
    () => {
      selectorSelected.value = {
        [ClusterTypes.TENDBCLUSTER]: slaves.value.map((item) => ({
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          instance_address: item.instance_address,
          ip: item.ip,
          port: item.port,
        })),
      } as unknown as InstanceSelectorValues<IValue>;
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .tendbcluster-checksum-slave-default {
    cursor: pointer;
    display: flex;
    align-items: center;
    width: 100%;
    justify-content: space-between;

    .tendbcluster-checksum-placeholder {
      color: #c4c6cc;
    }

    .render-slaves-icon {
      font-size: 15px;
      color: #979ba5;
    }
  }

  .tendbcluster-checksum-slave-selected {
    cursor: pointer;

    .render-slaves {
      display: flex;
      flex-direction: column;

      p {
        margin: 0;
        overflow: hidden;
        line-height: 20px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    &:hover {
      .edit-btn {
        display: flex;
      }
    }

    .edit-btn {
      position: absolute;
      inset: 0;
      display: none;
      justify-content: center;
      align-items: center;
      background-color: rgb(250 251 253 / 45%);

      &:hover {
        color: #3a84ff;
      }
    }
  }
</style>
