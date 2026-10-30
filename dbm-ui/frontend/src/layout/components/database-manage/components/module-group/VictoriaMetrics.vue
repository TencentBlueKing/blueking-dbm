<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <FunController module-id="k8s">
    <MenuGroup
      :db-type="DBTypes.K8S_VICTORIAMETRICS"
      :is-error="isError">
      <FunController
        controller-id="k8s_victoriametrics"
        module-id="k8s">
        <DbMenuItem
          icon="cluster"
          route-name="VictoriametricsClusterList">
          {{ t('标准集群') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER"
              role="cluster" />
          </template>
        </DbMenuItem>
        <DbMenuItem
          icon="node"
          route-name="VictoriametricsSelectList">
          {{ t('查询集群') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
              role="cluster" />
          </template>
        </DbMenuItem>
      </FunController>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import DbMenuItem from '../../../menu/Item.vue';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
