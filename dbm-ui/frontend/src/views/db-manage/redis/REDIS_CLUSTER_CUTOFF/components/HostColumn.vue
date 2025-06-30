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
    <EditableBlock
      v-if="modelValue?.master_ip"
      class="related-slave">
      <p>{{ t('关联 Slave') }}</p>
      <p>-- {{ modelValue.ip }}</p>
    </EditableBlock>
    <EditableInput
      v-else
      v-model="modelValue.ip"
      :placeholder="t('请输入如: 192.168.10.2')"
      @change="handleChange" />
  </EditableColumn>
  <ResourceSelector
    v-model:is-show="showSelector"
    v-model:selected="dataList"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';
  import { queryMasterSlavePairs } from '@services/source/redisToolbox';

  import { DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  import ResourceSelector, {
    type IValue
  } from './resource-selector/Index.vue';

  export type SelectorHost = IValue;

  interface Props {
    selected: {
      ip: string;
      role: string;
    }[];
    selectedMap: Record<string, boolean>
  }

  interface Emits {
    (e: 'batch-edit', list: IValue[]): void;
    (e: 'append', data: typeof modelValue.value): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_ids: number[];
    ip: string;
    master_domain: string;
    master_ip?: string;// 关联的主库ip，仅当role=redis_slave时存在
    role: string;
    slave_ip?: string; // 关联的从库ip，仅当role=redis_master时存在
    spec_config: SpecInfo;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const dataList = shallowRef<IValue[]>([]);

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'blur',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('IP 重复'),
      trigger: 'blur',
      validator: (value: string) => !value ||props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
  ];

  const { loading, run: queryMachine } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        const [cluster] = item.related_clusters;
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_ids: item.related_clusters.map(item=>item.id),
          ip: item.ip,
          master_domain: item.master_domain,
          role: item.role,
          spec_config: item.spec_config
        };
        if (cluster?.id && item.role !== 'proxy') {
          queryMasterSlavePairs({
            bk_biz_id: item.bk_biz_id,
            cluster_id: cluster.id
          }).then(data=>{
            // 若当前输入的ip为slave
            if (item.role === 'redis_slave') {
              const [{ master_ip: masterIp }] = data.filter((cur)=>cur.slave_ip===item.ip);
              if (!masterIp) {
                return
              }
              // 并且对应的master已经录入表格
              if (props.selectedMap[masterIp]) {
                modelValue.value.master_ip = masterIp;
              }
              return
            }

            // 若当前输入的ip为master
            // 并且找到对应的主从关系则追加slave
            if (item.role === 'redis_master') {
              const [{ slave_ip: slaveIp }] = data.filter((cur)=>cur.master_ip===item.ip);
              if (!slaveIp) {
                return
              }
              modelValue.value.slave_ip = slaveIp;
              emits('append', Object.assign(_.cloneDeep(modelValue.value), {
                ip: slaveIp,
                master_ip: item.ip,
                role: 'redis_slave',
                spec_config: item.spec_config
              }))
            }
          })
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
      spec_config: {} as SpecInfo
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
          instance_addresses: [modelValue.value.ip],
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(()=>props.selected, ()=>{
    if (props.selected.length > dataList.value.length) {
      dataList.value = props.selected.map(item=>({
        instance_role: item.role,
        ip: item.ip,
      })) as IValue[];
    }
  })
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .related-slave {
    height: 40px;
    color: #979ba5;
    background: #fafbfd;
  }
</style>
