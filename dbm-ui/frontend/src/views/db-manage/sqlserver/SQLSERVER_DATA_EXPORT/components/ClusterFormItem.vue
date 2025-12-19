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
  <BkFormItem
    error-display-type="tooltips"
    error-tip-append-to-parent
    :label="t('集群')"
    property="cluster_domain"
    required
    :rules="rules"
    style="width: 750px">
    <div class="cluster-form-item">
      <BkLoading :loading="isLoading">
        <BkInput
          v-model="clusterDomain"
          :autosize="{ minRows: 5, maxRows: 20 }"
          :over-max-length-limit="false"
          :placeholder="t('请输入导出集群或从拓扑选择，多个逗号或换行分隔')"
          :resize="false"
          style="width: 750px"
          type="textarea" />
      </BkLoading>
      <BkButton
        class="ml-8"
        @click="() => (isShowSelector = true)">
        <DbIcon
          style="margin-right: 6px; color: #979ba5"
          type="add" />
        {{ t('从拓扑添加') }}
      </BkButton>
    </div>
  </BkFormItem>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[clusterType]"
    :selected="selectedClusters"
    @change="handelClusterChange" />
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { filterClusters } from '@services/source/dbbase';

  import { type ClusterTypes, DBTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  export interface ClusterModelMap {
    [ClusterTypes.SQLSERVER_HA]: SqlServerHaModel;
    [ClusterTypes.SQLSERVER_SINGLE]: SqlServerSingleModel;
  }

  interface Props {
    clusterType: keyof ClusterModelMap;
  }

  type Emits = (e: 'change', data: ClusterModelMap[Props['clusterType']][]) => void;
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterDomain = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const isLoading = ref(false);
  const isShowSelector = ref(false);

  const selectedClusters = shallowRef<{ [key: string]: Array<ClusterModelMap[Props['clusterType']]> }>({
    [props.clusterType]: [],
  });

  const rules = [
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          emits('change', []);
          return true;
        }
        const formatError: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!domainRegex.test(item)) {
            formatError.push(item);
          }
        });
        return formatError.length ? t('集群域名格式不正确：xx', [formatError.join(',')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          emits('change', []);
          return true;
        }
        const domains = value.split(batchSplitRegex);
        isLoading.value = true;
        return filterClusters<SqlServerHaModel>({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: props.clusterType,
          db_type: DBTypes.SQLSERVER,
          exact_domain: domains.join(','),
        }).then((data) => {
          isLoading.value = false;
          const clusterIsExist = data.reduce<Record<string, boolean>>((acc, cluster) => {
            Object.assign(acc, {
              [cluster.master_domain]: true,
            });
            return acc;
          }, {});
          const notExists = domains.filter((domain) => !clusterIsExist[domain]);
          if (notExists.length > 0) {
            return t('目标集群xx不存在', [notExists.join(',')]);
          }
          emits('change', data);
          return true;
        });
      },
    },
  ];

  const handelClusterChange = (selected: { [key: string]: Array<ClusterModelMap[Props['clusterType']]> }) => {
    selectedClusters.value = selected;
    clusterDomain.value = selected[props.clusterType].map((item) => item.master_domain).join('\n');
    emits('change', selected[props.clusterType]);
  };
</script>
<style lang="less" scoped>
  .cluster-form-item {
    display: flex;
  }
</style>
