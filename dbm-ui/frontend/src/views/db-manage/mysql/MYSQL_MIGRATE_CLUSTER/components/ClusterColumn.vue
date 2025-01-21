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
    ref="column"
    :append-rules="rules"
    field="batchCluster.renderText"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="300"
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
      v-model="modelValue.renderText"
      :placeholder="t('请输入集群域名_多个集群用分隔符输入')"
      @change="handleInputChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      renderText: string;
      clusters: Record<
        string,
        {
          id: number;
          master_domain: string;
        }
      >;
    }[];
    selectedMap: Record<string, number>;
  }

  interface Emits {
    (e: 'batch-edit', list: TendbhaModel[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    renderText: string;
    clusters: Record<
      string,
      {
        id: number;
        master_domain: string;
      }
    >;
  }>({
    default: () => ({
      renderText: '',
      clusters: {},
    }),
  });

  const { t } = useI18n();
  const columnRef = useTemplateRef('column');

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbhaModel[]>>(() => ({
    [ClusterTypes.TENDBHA]: props.selected.flatMap((item) => item.clusters as unknown as TendbhaModel),
  }));

  const rules = [
    {
      validator: (value: string) => value.split(batchSplitRegex).every((item) => domainRegex.test(item)),
      message: t('集群域名格式不正确'),
      trigger: 'change',
    },
    {
      validator: (value: string) => {
        const repeats: string[] = [];
        const list = value.split(batchSplitRegex);
        list.forEach((item, index) => {
          // 同一个单元格内校验重复
          if (index !== list.indexOf(item)) {
            repeats.push(item);
          }
          // 另一行出现重复
          props.selected.forEach((rowData, rowIndex) => {
            if (rowIndex !== columnRef.value?.getRowIndex() && rowData.clusters[item]) {
              repeats.push(item);
            }
          });
        });
        return repeats.length ? t('目标集群xx重复', [repeats.join(',')]) : true;
      },
      message: '',
      trigger: 'blur',
    },
    {
      validator: (value: string) => {
        const notFounds: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!props.selectedMap[item]) {
            notFounds.push(item);
          }
        });
        return notFounds.length ? t('目标集群xx不存在', [notFounds.join(',')]) : true;
      },
      message: '',
      trigger: 'blur',
    },
  ];

  const { run: queryCluster, loading } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        let clusters = {};
        data.forEach((item) => {
          clusters = {
            ...clusters,
            [item.master_domain]: {
              id: item.id,
              master_domain: item.master_domain,
            },
          };
        });
        modelValue.value.clusters = clusters;
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value.clusters = {};
    if (value) {
      queryCluster({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        exact_domain: value.split(batchSplitRegex).join(','),
      });
    }
  };

  const handleSelectorChange = (selected: Record<string, TendbhaModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBHA]);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
