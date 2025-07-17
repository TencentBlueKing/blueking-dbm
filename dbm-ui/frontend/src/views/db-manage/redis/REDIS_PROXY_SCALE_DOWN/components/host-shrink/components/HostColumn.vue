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
    field="proxy_reduced_host.ip"
    fixed="left"
    :label="t('目标主机')"
    :loading="loading"
    :min-width="150"
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
      v-model="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleChange" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="selectedHosts"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { checkInstance } from '@services/source/dbbase';
  import { getRedisClusterList } from '@services/source/redis';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  export type SelectorHost = IValue;

  interface Props {
    selected: {
      bk_biz_id?: number;
      bk_cloud_id?: number;
      bk_host_id?: number;
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_id: number;
    ip: string;
    master_domain: string;
    role: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.REDIS]: [
      {
        id: 'redis',
        name: t('目标从库主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Proxy 主机'),
            role: 'proxy',
          },
        },
        topoConfig: {
          countFunc: (item: RedisModel) => item.proxyCount,
          getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
            getRedisClusterList({
              ...params,
              cluster_type: [
                ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                ClusterTypes.PREDIXY_REDIS_CLUSTER,
              ].join(','),
            }),
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.proxy.forEach((item) => ipSet.add(item.ip)));
            return ipSet.size;
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Proxy 主机'),
            role: 'proxy',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const showSelector = ref(false);
  const selectedHosts = computed<InstanceSelectorValues<IValue>>(() => ({
    [ClusterTypes.REDIS]: props.selected as IValue[],
  }));

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'change',
      validator: (value: string) => !value || props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('主机不包含任何 Proxy 实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'proxy',
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_id: item.cluster_id,
          ip: item.ip,
          master_domain: item.master_domain,
          role: item.role,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      ip: value,
      master_domain: '',
      role: '',
    };
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected[ClusterTypes.REDIS]);
  };

  watch(
    modelValue,
    () => {
      if (!modelValue.value.bk_host_id && modelValue.value.ip) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ],
          db_type: DBTypes.REDIS,
          instance_addresses: [modelValue.value.ip],
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
