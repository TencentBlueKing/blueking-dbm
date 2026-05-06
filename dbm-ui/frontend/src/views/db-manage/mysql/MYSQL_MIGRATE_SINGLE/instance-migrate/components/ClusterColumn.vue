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
    field="batchCluster.renderText"
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
      v-model="modelValue.renderText"
      :placeholder="t('请输入集群域名_多个集群用分隔符输入')"
      @change="handleInputChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBSINGLE]"
    :selected="selectedClusters"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
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

  type Emits = (e: 'batch-edit', list: TendbsingleModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    clusters: Record<
      string,
      {
        hostList: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
        id: number;
        master_domain: string;
        region: string;
      }
    >;
    renderText: string;
    spec_id_list: number[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbsingleModel[]>>(() => ({
    [ClusterTypes.TENDBSINGLE]: props.selected as TendbsingleModel[],
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

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbsingleModel>, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        let clusters = {};
        const spedIdList: number[] = [];
        data.forEach((item) => {
          spedIdList.push(item.cluster_spec?.spec_id);
          clusters = {
            ...clusters,
            [item.master_domain]: {
              hostList: item.masters.map((host) => ({
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: host.bk_cloud_id,
                bk_host_id: host.bk_host_id,
                ip: host.ip,
              })),
              id: item.id,
              master_domain: item.master_domain,
              region: item.region,
            },
          };
        });
        modelValue.value.clusters = clusters;
        modelValue.value.spec_id_list = spedIdList;
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      clusters: {},
      renderText: value,
      spec_id_list: [],
    };
  };

  const handleSelectorChange = (selected: Record<string, TendbsingleModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBSINGLE]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && _.isEmpty(modelValue.value.clusters)) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: ClusterTypes.TENDBSINGLE,
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
</style>
