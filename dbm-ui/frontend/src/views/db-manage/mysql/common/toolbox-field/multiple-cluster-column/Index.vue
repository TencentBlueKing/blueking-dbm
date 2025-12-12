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
    field="multipleCluster.renderText"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="350"
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
      :placeholder="t('请选择或输入集群（多个换行分隔）')"
      @change="handleChange">
      <template #append>
        <span v-bk-tooltips="t('选择集群')">
          <DbIcon
            class="select-icon"
            type="host-select"
            @click="handleShowSelector" />
        </span>
      </template>
    </EditableTextarea>
  </EditableColumn>
  <EditableColumn
    :label="t('关联实例')"
    :loading="loading"
    :min-width="250"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-for="cluster in modelValue.clusters"
        :key="cluster.id">
        <p>
          {{ cluster.master_domain }}
        </p>
        <p
          v-for="instance in cluster.proxies"
          :key="instance.bk_instance_id"
          style="color: #979ba5">
          --{{ instance.instance }}
        </p>
      </div>
    </EditableBlock>
  </EditableColumn>
  <!-- 表头批量添加 -->
  <ClusterSelector
    v-model:is-show="showBatchSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
    @change="handleSelectorBatchChange" />
  <!-- 单元格添加 -->
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="clusterTypes"
    :selected="currentClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    clusterTypes?: ClusterTypes[];
    selected: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    }[];
    selectedMap: Record<string, boolean>;
  }

  type Emits = (e: 'batch-edit', list: any[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [ClusterTypes.TENDBHA],
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    city: string;
    clusters: TendbhaModel[];
    renderText: string;
    spec_ids: number[];
    subzones: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const showBatchSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbhaModel[]>>(() => ({
    [ClusterTypes.TENDBHA]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.TENDBHA,
    ) as TendbhaModel[],
    [ClusterTypes.TENDBSINGLE]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.TENDBSINGLE,
    ) as TendbhaModel[],
  }));
  const currentClusters = computed<Record<string, TendbhaModel[]>>(() => ({
    [ClusterTypes.TENDBHA]: modelValue.value.clusters.filter((item) => item.cluster_type === ClusterTypes.TENDBHA),
    [ClusterTypes.TENDBSINGLE]: modelValue.value.clusters.filter(
      (item) => item.cluster_type === ClusterTypes.TENDBSINGLE,
    ),
  }));
  const selectedCounter = computed(() => _.countBy(props.selected, 'master_domain'));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'blur',
      validator: (value: string) => !value || value.split(batchSplitRegex).every((item) => domainRegex.test(item)),
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
        return repeats.length ? t('目标集群xx重复', [repeats.join(',')]) : true;
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
        return notFounds.length ? t('目标集群xx不存在', [notFounds.join(',')]) : true;
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbhaModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const spedIdsSet = new Set<number>();
        const citiesSet = new Set<string>();
        const subzonesSet = new Set<string>();
        data.forEach((item) => {
          // 规格ID
          if (item.cluster_spec?.spec_id) {
            spedIdsSet.add(item.cluster_spec.spec_id);
          }

          // 地域信息
          if (item.region && item.region !== 'default') {
            citiesSet.add(item.region);
          }

          // 园区信息
          (item?.cluster_subzones || []).forEach((zone) => {
            subzonesSet.add(zone);
          });
        });
        modelValue.value.clusters = data;
        modelValue.value.spec_ids = Array.from(spedIdsSet);
        modelValue.value.city = Array.from(citiesSet).join(',');
        modelValue.value.subzones = Array.from(subzonesSet).join(',');
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
        city: '',
        clusters: [],
        renderText: value
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter((line) => line.length > 0)
          .join('\n'),
        spec_ids: [],
        subzones: '',
      },
    );
  };

  const handleSelectorBatchChange = (selected: Record<string, TendbhaModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', list);
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    handleChange(list.map((item) => item.master_domain).join('\n'));
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && !modelValue.value.clusters.length) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: props.clusterTypes.join(','),
          db_type: DBTypes.MYSQL,
          exact_domain: modelValue.value.renderText.split(batchSplitRegex).join(','),
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
