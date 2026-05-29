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
    field="cluster.master_domain"
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
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入集群域名')"
      @change="handleChange" />
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selectedClusters"
    support-offline-data
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    /**
     * 集群禁用配置：用于在选择器和手动输入域名场景下统一拦截不可选集群（如正常状态集群）
     */
    disableSelectConfig?: {
      /** 命中时返回 true 表示该集群不可选 */
      handler: (data: TendbClusterModel) => boolean;
      /** 不可选时的提示文案 */
      tip: string;
    };
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: TendbClusterModel[]) => void;

  interface Exposes {
    fetchData: (
      tableData: {
        cluster: ClusterSpecModel;
      }[],
    ) => void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<ClusterSpecModel>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedClusters = computed<Record<string, TendbClusterModel[]>>(() => ({
    [ClusterTypes.TENDBCLUSTER]: props.selected as TendbClusterModel[],
  }));

  const tabListConfig = computed<Record<string, TabConfig> | undefined>(() => {
    if (!props.disableSelectConfig) {
      return undefined;
    }
    const { handler, tip } = props.disableSelectConfig;
    return {
      [ClusterTypes.TENDBCLUSTER]: {
        disabledRowConfig: [
          {
            handler: (data: any) => handler(data as TendbClusterModel),
            tip,
          },
        ],
      } as TabConfig,
    };
  });

  // 手动输入域名时存储查询到的集群信息，用于校验是否被禁用
  const queriedCluster = shallowRef<TendbClusterModel>();

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'blur',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) => !value || props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
    {
      message: () => props.disableSelectConfig?.tip || t('该集群不可选'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value || !modelValue.value.id || !props.disableSelectConfig || !queriedCluster.value) {
          return true;
        }
        return !props.disableSelectConfig.handler(queriedCluster.value);
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<TendbClusterModel>, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        queriedCluster.value = new TendbClusterModel(item);
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          id: item.id,
          master_domain: item.master_domain,
          mnt_count: item.spider_mnt.length,
          region: item.region,
          spider_master: item.spider_master,
          spider_master_spec_list: item.spider_master.map((host) => host.spec_config.id),
          spider_slave: item.spider_slave,
          spider_slave_spec_list: item.spider_slave.map((host) => host.spec_config.id),
        };
      } else {
        queriedCluster.value = undefined;
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    queriedCluster.value = undefined;
    modelValue.value = {
      bk_cloud_id: 0,
      id: 0,
      master_domain: value,
      mnt_count: 0,
      region: '',
      spider_master: [],
      spider_master_spec_list: [],
      spider_slave: [],
      spider_slave_spec_list: [],
    };
    queryCluster({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: ClusterTypes.TENDBCLUSTER,
      db_type: DBTypes.TENDBCLUSTER,
      exact_domain: value,
    });
  };

  const handleSelectorChange = (selected: Record<string, TendbClusterModel[]>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBCLUSTER]);
  };

  defineExpose<Exposes>({
    fetchData(
      tableData: {
        cluster: ClusterSpecModel;
      }[],
    ) {
      const domainList = tableData.map((item) => item.cluster.master_domain);
      if (!domainList.length) {
        return;
      }

      filterClusters<TendbClusterModel>({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_type: ClusterTypes.TENDBCLUSTER,
        db_type: DBTypes.TENDBCLUSTER,
        exact_domain: domainList.join(','),
      }).then((data) => {
        data.forEach((cluster) => {
          const target = tableData.find((item) => item.cluster.master_domain === cluster.master_domain);
          if (target) {
            target.cluster = {
              bk_cloud_id: cluster.bk_cloud_id,
              id: cluster.id,
              master_domain: cluster.master_domain,
              mnt_count: cluster.spider_mnt.length,
              region: cluster.region,
              spider_master: cluster.spider_master,
              spider_master_spec_list: cluster.spider_master.map((host) => host.spec_config.id),
              spider_slave: cluster.spider_slave,
              spider_slave_spec_list: cluster.spider_slave.map((host) => host.spec_config.id),
            };
          }
        });
      });
    },
  });
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
