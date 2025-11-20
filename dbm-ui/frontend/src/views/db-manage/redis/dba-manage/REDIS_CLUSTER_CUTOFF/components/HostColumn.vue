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
    field="host.ip"
    fixed="left"
    :label="t('待替换主机')"
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
    <div
      :class="{
        'has-related': Boolean(modelValue.related_slave?.bk_host_id),
      }"
      style="flex: 1">
      <EditableInput
        v-model="modelValue.ip"
        :placeholder="t('请输入如: 192.168.10.2')"
        @change="handleChange" />
      <BkLoading
        v-if="modelValue.related_slave?.bk_host_id"
        class="related-slave"
        :loading="relatedLoading">
        <p>{{ t('关联 Slave') }}</p>
        <p>-- {{ modelValue.related_slave?.ip }}</p>
      </BkLoading>
    </div>
  </EditableColumn>
  <MachineResourceSelector
    v-model:is-show="showSelector"
    v-model:selected="dataList"
    :cluster-types="[ClusterTypes.REDIS]"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getGlobalMachine } from '@services/source/dbbase';
  import { queryMasterSlavePairs } from '@services/source/redisToolbox';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import MachineResourceSelector, { type IMachine } from '@components/machine-resource-selector/Index.vue';

  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  export type IValue = IMachine;

  interface Props {
    selected: Array<typeof modelValue.value>;
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_ids: number[];
    ip: string;
    master_domain: string;
    related_slave?: {
      bk_host_id: number;
      ip: string;
      spec_config: SpecInfo;
    }; // 关联的从库ip，仅当role=redis_master时存在
    role: string;
    spec_config: SpecInfo;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const dataList = shallowRef<IValue[]>([]);

  // 铺平获取关联的从库ip，用于校验
  const allIps = computed(() => props.selected.flatMap((item) => [item.ip, item.related_slave?.ip].filter(Boolean)));

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('IP 重复'),
      trigger: 'change',
      validator: (value: string) => !value || allIps.value.filter((ip) => ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
  ];

  const { loading: relatedLoading, run: queryRelatedSlave } = useRequest(queryMasterSlavePairs, {
    manual: true,
    onSuccess: (data) => {
      const [{ slaves }] = data.filter((cur) => cur.master_ip === modelValue.value.ip);
      if (slaves) {
        modelValue.value.related_slave = {
          bk_host_id: slaves.bk_host_id,
          ip: slaves.ip,
          spec_config: slaves.spec_config,
        };
      }
    },
  });

  const { loading, run: queryMachine } = useRequest(getGlobalMachine, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data.results;
      if (item) {
        const [cluster] = item.related_clusters;
        modelValue.value = {
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_ids: item.related_clusters.map((item) => item.id),
          ip: item.ip,
          master_domain: cluster?.immute_domain || '',
          role: item.instance_role,
          spec_config: item.spec_config,
        };
        if (item.instance_role === 'redis_master') {
          queryRelatedSlave({
            bk_biz_id: item.bk_biz_id,
            cluster_id: cluster.id,
          });
        }
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_ids: [] as number[],
      ip: value,
      master_domain: '',
      role: '',
      spec_config: {} as SpecInfo,
    };
  };

  const handleSelectorChange = (selected: IValue[]) => {
    emits('batch-edit', selected);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryMachine({
          db_type: DBTypes.REDIS,
          ip: modelValue.value.ip,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.selected,
    () => {
      dataList.value = props.selected.map(
        (item) =>
          ({
            bk_biz_id: item.bk_biz_id,
            instance_role: item.role,
            ip: item.ip,
          }) as IValue,
      );
    },
  );
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .related-slave {
    height: 40px;
    padding: 0 8px;
    line-height: 18px;
    color: #979ba5;
    background: #fafbfd;
  }
</style>
