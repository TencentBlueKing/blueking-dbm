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
    field="batchCluster.clusters"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="350"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableTextarea
      v-model="localValue"
      :placeholder="t('请选择或输入集群（多个换行分隔）')"
      @change="handleInputChange" />
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
          v-for="instance in cluster.masters"
          :key="instance.bk_instance_id"
          style="color: #979ba5">
          --{{ instance.instance }}
        </p>
      </div>
    </EditableBlock>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
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
    selected: {
      id: number;
      master_domain: string;
    }[];
    selectedMap: Record<string, boolean>;
  }

  type Emits = (e: 'batch-edit', list: TendbhaModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    cities: string[];
    clusters: Array<TendbhaModel>;
    spec_id_list: number[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const localValue = ref('');
  const selectedClusters = computed<Record<string, TendbhaModel[]>>(() => ({
    [ClusterTypes.TENDBHA]: props.selected as TendbhaModel[],
  }));
  const selectedCounter = computed(() => _.countBy(props.selected, 'master_domain'));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'blur',
      validator: (value: string) =>
        !value || localValue.value.split(batchSplitRegex).every((item) => domainRegex.test(item)),
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const repeats: string[] = [];
        const list = localValue.value.split(batchSplitRegex);
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
        localValue.value.split(batchSplitRegex).forEach((item) => {
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
        const clusterList: TendbhaModel[] = [];
        const spedIdList: number[] = [];
        const cities: string[] = [];
        data.forEach((item) => {
          clusterList.push(item);
          spedIdList.push(item.cluster_spec?.spec_id);
          cities.push(item.region);
        });
        modelValue.value.clusters = clusterList;
        modelValue.value.spec_id_list = spedIdList;
        modelValue.value.cities = cities;
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = Object.assign(
      {},
      {
        cities: [],
        clusters: [],
        spec_id_list: [],
      },
    );
    queryCluster({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: ClusterTypes.TENDBHA,
      db_type: DBTypes.MYSQL,
      exact_domain: value.split(batchSplitRegex).join(','),
    });
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.clusters.length && !localValue.value) {
        const domains = modelValue.value.clusters.map((cluster) => cluster.master_domain);
        localValue.value = domains.join('\n');
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: ClusterTypes.TENDBHA,
          db_type: DBTypes.MYSQL,
          exact_domain: domains.join(','),
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
</style>
