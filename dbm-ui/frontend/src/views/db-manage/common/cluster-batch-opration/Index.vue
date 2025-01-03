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
  <BkDropdown
    :key="renderKey"
    v-bk-tooltips="{
      disabled: !disabled,
      content: t('请选择操作集群'),
    }"
    class="cluster-batch-operation"
    :disabled="disabled"
    :popover-options="popoverOptions"
    @click.stop
    @hide="() => (isShowDropdown = false)"
    @show="() => (isShowDropdown = true)">
    <BkButton :disabled="disabled">
      {{ t('批量操作') }}
      <DbIcon
        class="cluster-batch-operation-icon ml-4"
        :class="[{ 'cluster-batch-operation-icon-active': isShowDropdown }]"
        type="up-big " />
    </BkButton>
    <template #content>
      <BkDropdownMenu class="cluster-batch-operation-popover">
        <Component
          :is="content"
          v-model:side-slider-show="sideSliderShow"
          :selected="selected"
          @success="handleSuccess">
        </Component>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import TendbHaModel from '@services/model/mysql/tendbha';
  import TendbSingleModel from '@services/model/mysql/tendbsingle';
  import RedisModel from '@services/model/redis/redis';
  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlserverSingleModel from '@services/model/sqlserver/sqlserver-single';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { ClusterTypes } from '@common/const';

  interface ClusterModelMap {
    [ClusterTypes.TENDBSINGLE]: TendbSingleModel;
    [ClusterTypes.TENDBHA]: TendbHaModel;
    [ClusterTypes.TENDBCLUSTER]: TendbClusterModel;
    [ClusterTypes.REDIS]: RedisModel;
    [ClusterTypes.REDIS_INSTANCE]: RedisModel;
    [ClusterTypes.MONGO_REPLICA_SET]: MongodbModel;
    [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModel;
    [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModel;
    [ClusterTypes.SQLSERVER_HA]: SqlserverHaModel;
  }
</script>
<script setup lang="ts" generic="T extends keyof ClusterModelMap">
  interface Props {
    selected: ClusterModelMap[T][];
    clusterType: T;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const contentModule = import.meta.glob<{
    default: () => {
      name: T;
    };
  }>('./components/*/Index.vue', {
    eager: true,
  });

  const isShowDropdown = ref(false);
  const sideSliderShow = ref(false);
  const renderKey = ref(new Date().getTime());

  const disabled = computed(() => props.selected.length === 0);

  const content = computed(() => {
    const renderModule = _.find(
      Object.values(contentModule),
      (moduleItem) => moduleItem.default.name === props.clusterType,
    );

    if (renderModule) {
      return renderModule.default;
    }

    return null;
  });

  const popoverOptions = computed(() => ({
    boundary: 'body',
    disableOutsideClick: sideSliderShow.value,
    clickContentAutoHide: true,
    renderDirective: 'show',
  }));

  watch(sideSliderShow, () => {
    if (!sideSliderShow.value) {
      renderKey.value = new Date().getTime();
    }
  });

  const handleSuccess = () => {
    emits('success');
  };
</script>

<style lang="less">
  .cluster-batch-operation-popover {
    .bk-dropdown-item {
      padding: 0;

      .opration-button {
        width: 100%;
        padding: 0 16px;
      }
    }
  }
</style>

<style lang="less" scoped>
  .cluster-batch-operation {
    .cluster-batch-operation-icon {
      transform: rotate(0);
      transition: all 0.2s;
    }

    .cluster-batch-operation-icon-active {
      transform: rotate(180deg);
    }
  }
</style>
