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
    :append-rules="rules"
    field="originProxies.renderText"
    fixed="left"
    :label="t('目标Proxy实例')"
    :loading="loading"
    :min-width="300"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowBatchSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableTextarea
      v-model="modelValue.renderText"
      :placeholder="t('请输入实例，多个实例用分隔符输入')"
      @change="handleChange">
      <template #append>
        <span v-bk-tooltips="t('选择实例')">
          <DbIcon
            class="select-icon"
            type="host-select"
            @click="handleShowSelector" />
        </span>
      </template>
    </EditableTextarea>
  </EditableColumn>
  <EditableColumn
    :label="t('关联集群')"
    :loading="loading"
    :min-width="240"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <p
        v-for="domain in Object.keys(clusterMemo)"
        :key="domain">
        {{ domain }}
      </p>
    </EditableBlock>
  </EditableColumn>
  <!-- 表头批量添加 -->
  <InstanceSelector
    v-model:is-show="showBatchSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    hide-manual-input
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorBatchChange" />
  <!-- 单元格添加 -->
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    hide-manual-input
    :selected="selectedCellInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { batchSplitRegex, ipPort } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  export type SelectorItem = IValue;

  interface Props {
    selected: IValue[];
    selectedMap: Record<string, IValue>;
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cities: string[];
    cluster_ids: number[];
    instances: IValue[];
    renderText: string;
    spec_ids: number[];
    subzones: string[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        id: ClusterTypes.TENDBHA,
        name: t('目标实例'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: t('Proxy 实例'),
            role: 'proxy',
          },
        },
        topoConfig: {
          countFunc: (item: TendbhaModel) => item.proxies.length,
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: t('Proxy 实例'),
            role: 'proxy',
          },
        },
      },
    ],
  } as Record<ClusterTypes, PanelListType>;

  const clusterMemo = ref<Record<string, boolean>>({});
  const showSelector = ref(false);
  const showBatchSelector = ref(false);
  const selectedInstances = computed(() => ({
    [ClusterTypes.TENDBHA]: props.selected,
  }));
  const selectedCellInstances = computed(() => ({
    [ClusterTypes.TENDBHA]: modelValue.value.instances,
  }));
  const selectedCounter = computed(() => _.countBy(props.selected, 'instance_address'));

  const rules = [
    {
      message: t('实例格式有误，请输入 IP:Port'),
      trigger: 'change',
      validator: (value: string) => !value || value.split(batchSplitRegex).every((item) => ipPort.test(item)),
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const repeats: string[] = [];
        const list = value.split(batchSplitRegex);
        list.forEach((domain, index) => {
          if (index !== list.indexOf(domain)) {
            repeats.push(domain);
          } else if (selectedCounter.value[domain] > 1) {
            repeats.push(domain);
          }
        });
        return repeats.length ? t('目标实例xx重复', [repeats.join(',')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const notFounds: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!props.selectedMap[item]) {
            notFounds.push(item);
          }
        });
        return notFounds.length ? t('目标实例xx不存在', [notFounds.join(',')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const roleErrors: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (props.selectedMap[item].role !== 'proxy') {
            roleErrors.push(item);
          }
        });
        return roleErrors.length ? t('实例xx为非 Proxy 实例，请选择 Proxy 实例', [roleErrors.join(',')]) : true;
      },
    },
  ];

  const { loading, run: queryInstance } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        // 使用 Set 去重，提高性能并避免重复数据
        const spedIdsSet = new Set<number>();
        const citiesSet = new Set<string>();
        const subzonesSet = new Set<string>();
        const clusterIdsSet = new Set<number>();
        const clusterMap: Record<string, boolean> = {};
        const instances: Record<string, IValue> = {};

        data.forEach((item) => {
          // 规格ID
          if (item.spec_config?.id) {
            spedIdsSet.add(item.spec_config.id);
          }

          // 地域信息
          if (item.related_clusters?.[0]?.region && item.related_clusters[0].region !== 'default') {
            citiesSet.add(item.related_clusters[0].region);
          }

          // 园区信息
          (item.related_clusters?.[0]?.zone_list || []).forEach((zone) => {
            subzonesSet.add(zone);
          });

          // 集群ID
          clusterIdsSet.add(item.cluster_id);

          Object.assign(clusterMap, {
            [item.master_domain]: true,
          });

          Object.assign(instances, {
            [item.instance_address]: item,
          });
        });

        clusterMemo.value = clusterMap;
        modelValue.value.instances = data as unknown as IValue[];
        modelValue.value.spec_ids = Array.from(spedIdsSet);
        modelValue.value.cities = Array.from(citiesSet);
        modelValue.value.subzones = Array.from(subzonesSet);
        modelValue.value.cluster_ids = Array.from(clusterIdsSet);
      }
    },
  });

  const handleShowBatchSelector = () => {
    showBatchSelector.value = true;
  };

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = Object.assign(
      {},
      {
        cities: [],
        cluster_ids: [],
        instances: [],
        renderText: value
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter((line) => line.length > 0)
          .join('\n'),
        spec_ids: [],
        subzones: [],
      },
    );
  };

  const handleSelectorBatchChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    handleChange(list.map((item) => item.instance_address).join('\n'));
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && !modelValue.value.instances.length) {
        queryInstance({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA],
          db_type: DBTypes.MYSQL,
          instance_addresses: modelValue.value.renderText.split(batchSplitRegex),
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .select-icon {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
