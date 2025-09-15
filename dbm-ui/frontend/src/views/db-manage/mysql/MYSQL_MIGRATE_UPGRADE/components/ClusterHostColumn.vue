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
    :disabled-method="disabledMethod"
    :label="t('主从主机')"
    :min-width="200"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <div v-if="master?.bk_host_id && slave?.bk_host_id">
        <div class="host-item">
          <div class="host-tag host-tag-master">M</div>
          {{ master.ip }}
        </div>
        <div class="host-item">
          <div class="host-tag host-tag-slave">S</div>
          {{ slave.ip }}
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    :label="t('只读主机')"
    :min-width="200"
    readonly>
    <EditableBlock :placeholder="!readonlyHost.length ? t('无只读主机') : t('自动生成')">
      <div v-if="readonlyHost.length">
        <div
          v-for="host in readonlyHost"
          :key="host.ip">
          {{ host.ip }}
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import type { ClusterTypes } from '@common/const';

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    } & TendbhaModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const master = computed(() => props.cluster.masters?.[0] || {});
  const slave = computed(() => props.cluster.slaves?.filter((item) => item.is_stand_by)?.[0] || {});
  const readonlyHost = computed(() => props.cluster.slaves?.filter((item) => !item.is_stand_by) || []);

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };
</script>
<style lang="less" scoped>
  .host-item {
    display: flex;
    align-items: center;

    .host-tag {
      width: 16px;
      height: 16px;
      margin-right: 4px;
      font-size: @font-size-mini;
      font-weight: bolder;
      line-height: 16px;
      text-align: center;
    }

    .host-tag-master {
      color: @primary-color;
      background-color: #cad7eb;
    }

    .host-tag-slave {
      color: #2dcb56;
      background-color: #c8e5cd;
    }
  }
</style>
