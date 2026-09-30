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
    :label="t('复制源')"
    :min-width="200"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <template v-if="dataSource.address">
        <span class="copy-source">
          <span class="copy-source__addr">{{ dataSource.address }}</span>
          <span class="copy-source__role">{{ dataSource.role }}</span>
        </span>
      </template>
    </EditableBlock>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getOracleHaInstanceList } from '@services/source/oracleHaCluster';

  import { ClusterInstStatusKeys } from '@common/const';

  import type { HostInfo } from '../types';
  import { buildHostInfo } from '../types';

  interface Props {
    // 上游实例所属集群
    clusterId: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    address: string;
    master: HostInfo | null;
    node: HostInfo | null;
    role: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  // 复制源展示值（仅主库模式渲染该列，其余模式由父级 v-if 隐藏）
  const dataSource = computed(() => (props.clusterId ? modelValue.value : { address: '', role: '' }));

  const { run: queryClusterInstances } = useRequest(getOracleHaInstanceList, {
    manual: true,
    onSuccess: (data) => {
      const instances = data.results.filter((item) => item.status === ClusterInstStatusKeys.RUNNING);
      if (!instances.length) {
        return;
      }
      const healthyStandbys = instances.filter((item) => item.role === 'standby').sort((a, b) => a.id - b.id);
      // 待 PEER 确认：DG 应用无中断、延迟在阈值内的判定字段，当前先按 status 判定
      const target = healthyStandbys.length ? healthyStandbys[0] : instances.find((item) => item.role === 'primary');
      if (target) {
        // 级联场景：复制源为从库（old_node），同时记录主库（old_master）
        const masterInstance = instances.find((item) => item.role === 'primary');
        modelValue.value = {
          address: target.instance_address,
          master: target.role === 'standby' && masterInstance ? buildHostInfo(masterInstance) : null,
          node: target.role === 'standby' ? buildHostInfo(target) : null,
          role: target.role,
        };
      }
    },
  });

  watch(
    () => props.clusterId,
    () => {
      modelValue.value = {
        address: '',
        master: null,
        node: null,
        role: '',
      };
      if (props.clusterId) {
        queryClusterInstances({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterId,
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .copy-source {
    display: inline-flex;
    column-gap: 8px;
    align-items: baseline;

    &__addr {
      font-family: 'JetBrains Mono', Consolas, monospace;
      font-size: 12px;
      color: #313238;
    }

    &__role {
      font-size: 12px;
      color: #979ba5;
    }
  }
</style>
