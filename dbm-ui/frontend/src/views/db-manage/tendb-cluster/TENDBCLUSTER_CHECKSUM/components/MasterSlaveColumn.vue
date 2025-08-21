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
    :rowspan="rowspan"
    required>
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
    :required="scope !== 'all'">
    <EditableBlock class="tendbcluster-checksum-render-slave-box">
      <div v-if="scope === 'all'">
        {{ t('全部') }}
      </div>
      <div v-else>
        <div class="render-slaves">
          <p
            v-for="instance in selected"
            :key="instance">
            {{ instance }}
          </p>
        </div>
        <div
          class="bk-editable-text-content-placeholder"
          v-if="selected.length < 1 || selected.every((item) => !item)"
          @click="handleShowSelector">
          {{ t('请选择') }}
        </div>
      </div>
      <div
        v-if="selected.length > 0 && scope !== 'all'"
        class="edit-btn"
        @click="handleShowSelector">
        <DbIcon type="edit" />
      </div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="master.instance_address"
    :label="t('校验主库')"
    :min-width="180"
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
    :tab-list-config="tabListConfig"
    :selected="selectorSelected"
    @change="handleChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { useRequest } from 'vue-request';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';
  import _ from 'lodash';
  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import { ClusterTypes } from '@common/const';

  type SlaveItem = ServiceReturnType<typeof getTendbclusterInstanceList>['results'][0];
  type MasterItem = SlaveItem['related_pair_instance'];

  interface InstanceInfo {
    ip: string;
    port: number;
    instance_address: string;
    bk_cloud_id: number;
    bk_biz_id: number;
    bk_host_id: number;
  }

  interface RowData {
    cluster: TendbClusterModel;
    table_patterns: string[];
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    scope: string;
    master: typeof master.value;
    slaves: typeof slaves.value;
    rowspan: number;
  }

  interface Props {
    cluster: TendbClusterModel;
    rowspan?: number;
  }

  interface Emits {
    (e: 'change'): void;
  }

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
            name: t('主库故障主机'),
            tableConfig: {
              firsrColumn: {
                field: 'instance_address',
                label: 'slave',
                role: 'backend_slave,backend_repeater,remote_slave,remote_repeater',
              },
            },
            topoConfig: {
              filterClusterId: props.cluster.id,
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

  const { run: fetchData } = useRequest(getTendbclusterInstanceList, {
    manual: true,
    onSuccess(data) {
      if (slaves.value.length && data.results.length > 0) {
        scope.value = 'partial';
        const slavesMap = Object.fromEntries(slaves.value.map((slave) => [slave.instance_address, true]));
        const instances = data.results.filter((item) => slavesMap[item.instance_address]);
        selected.value = instances.map((item) => item.instance_address);
        handleChange({
          [ClusterTypes.TENDBCLUSTER]: instances,
        } as unknown as InstanceSelectorValues<IValue>);
      }
    },
  });

  const handleShowSelector = () => {
    isShowInstanceSelector.value = true;
  };

  /**
   * 辅助查找实例所在行
   */
  const masterRowIndex: Record<string, number> = {};

  /**
   * 转换master数据
   */
  const generateMaster = (data: MasterItem) => ({
    ip: data.ip,
    port: data.port,
    instance_address: data.instance,
    bk_host_id: data.bk_host_id,
    bk_cloud_id: data.bk_cloud_id,
    bk_biz_id: data.bk_biz_id,
  });

  /**
   * 转换slave单项数据
   */
  const generateSlave = (data: IValue) => ({
    ip: data.ip,
    port: data.port,
    instance_address: data.instance_address,
    bk_host_id: data.bk_host_id,
    bk_cloud_id: data.bk_cloud_id,
    bk_biz_id: data.bk_biz_id,
  });

  const handleAppend = (data: { master: RowData['master']; slaves: RowData['slaves'] }) => {
    tableData.value.forEach((item, index) => {
      masterRowIndex[item.master.instance_address] = index;
    });

    const rowIndex = columnRef.value!.getRowIndex();
    const existIndex = masterRowIndex[data.master.instance_address];
    if (existIndex > -1) {
      tableData.value[existIndex] = Object.assign(_.cloneDeep(tableData.value[rowIndex]), {
        slaves: _.sortBy(
          _.uniqBy([...tableData.value[existIndex].slaves, ...data.slaves], 'instance_address'),
          'instance_address',
        ),
      });
    } else {
      tableData.value.splice(rowIndex + 1, 0, Object.assign(_.cloneDeep(tableData.value[rowIndex]), data));
    }
  };

  const handleChange = (payload: InstanceSelectorValues<IValue>) => {
    const selectedInstances = payload[ClusterTypes.TENDBCLUSTER];

    if (!selectedInstances.length) {
      slaves.value = [];
      master.value = {
        ip: '',
        port: 0,
        instance_address: '',
        bk_host_id: 0,
        bk_cloud_id: 0,
        bk_biz_id: 0,
      };
      return;
    }
    // 以master分组
    const masterGroup = _.groupBy(selectedInstances, (item) => item.related_pair_instance.instance);
    // 当前行的主库
    const currentMaster = selectedInstances[0].related_pair_instance;
    // 当前行的从库
    const currentSlaves = masterGroup[currentMaster.instance];
    slaves.value = currentSlaves.map((item) => generateSlave(item));
    master.value = generateMaster(currentMaster);
    // 追加其他行
    Object.entries(masterGroup).forEach(([master, slaves]) => {
      if (master !== currentMaster.instance) {
        const masterInfo = masterGroup[master][0].related_pair_instance;
        handleAppend({
          master: generateMaster(masterInfo),
          slaves: slaves.map((item) => generateSlave(item)),
        });
      }
    });
    selected.value = currentSlaves.map((item) => item.instance_address);

    // 触发行合并
    emits('change');
  };

  const handleChangeScope = (value: string) => {
    if (value === 'all') {
      const rowIndex = masterRowIndex[master.value.instance_address];
      const rowspan = tableData.value[rowIndex].rowspan;
      if (rowspan) {
        tableData.value.splice(rowIndex + 1, rowspan - 1);
      }
    } else {
      selected.value = [];
      slaves.value = [];
      master.value = {
        instance_address: '',
        ip: '',
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        port: 0,
      };
    }
  };

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        fetchData({
          cluster_id: props.cluster.id,
          role: 'backend_slave,backend_repeater,remote_slave,remote_repeater',
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(slaves, (newList, oldList) => {
    if (newList.length !== oldList.length) {
      selected.value = slaves.value.map((item) => item.instance_address);
    }
  });
</script>
<style lang="less">
  .tendbcluster-checksum-render-slave-box {
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
