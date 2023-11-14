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
  <div
    class="render-slave-box"
    :class="{
      'is-disabled': !clusterId || scope === 'all'
    }">
    <div v-if="scope === 'all'">
      {{ t('全部') }}
    </div>
    <div v-else>
      <div
        v-for="item in localSlaveInstanceList"
        :key="item"
        class="content">
        {{ item }}
      </div>
      <div
        v-if="localSlaveInstanceList.length < 1"
        style="color:#c4c6cc;"
        @click="handleShowBatchSelector">
        {{ t('请选择') }}
      </div>
    </div>
    <div
      v-if="localSlaveInstanceList.length > 0"
      class="edit-btn"
      @click="handleShowBatchSelector">
      <DbIcon type="edit" />
    </div>
    <InstanceSelector
      v-model:is-show="isShowInstanceSelector"
      :cluster-types="[ClusterTypes.TENDBCLUSTER]"
      :tab-list-config="tabListConfig"
      @change="handelInstanceSelectorChange" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector-new/Index.vue';

  interface Props {
    clusterId: number,
    scope: string,
  }
  interface Emits {
    (e: 'change', value: string[]): void
  }
  interface Exposes {
    getValue: () => Promise<string[]>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowInstanceSelector = ref(false);

  const localSlaveInstanceList = shallowRef<string[]>([]);

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: [{
      name: t('主库故障主机'),
      topoConfig: {
        filterClusterId: props.clusterId,
      },
      tableConfig: {
        firsrColumn: {
          label: 'slave', field: 'instance_address', role: 'remote_slave',
        },
      },
    }],
  } as unknown as Record<ClusterTypes, PanelListType>;

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowInstanceSelector.value = true;
  };

  // 批量选择
  const handelInstanceSelectorChange = (payload: InstanceSelectorValues) => {
    localSlaveInstanceList.value = payload.tendbcluster.map(item => item.instance_address);
    emits('change', [...localSlaveInstanceList.value]);
  };


  defineExpose<Exposes>({
    getValue() {
      if (props.scope === 'all') {
        return Promise.resolve(['']);
      }
      return Promise.resolve(localSlaveInstanceList.value);
    },
  });
</script>
<style lang="less" scoped>
  .render-slave-box{
    position: relative;
    padding: 0 16px;
    cursor: pointer;

    &.is-disabled{
      pointer-events: none;
      cursor: not-allowed;
      background-color: #fafbfd;
    }

    &:hover{
      .edit-btn{
        display: flex;
      }
    }

    .content {
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .edit-btn{
      position: absolute;
      inset: 0;
      display: none;
      justify-content: center;
      align-items: center;
      background-color: rgb(250 251 253 / 70%);

      &:hover{
        color: #3a84ff;
      }
    }
  }
</style>
