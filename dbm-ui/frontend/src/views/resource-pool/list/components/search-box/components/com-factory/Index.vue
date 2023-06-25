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
    class="resourece-pool-serach-item"
    :style="styles">
    <div class="wrapper">
      <div class="search-item-label">
        {{ config.label }}
      </div>
      <Component
        :is="renderCom"
        :default-value="model[name]"
        :model="model"
        :name="name"
        v-bind="{ ...inhertProps, ...listeners }"
        @change="handleChange" />
      <div
        v-if="errorMessage"
        class="search-item-error">
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref } from 'vue';

  import {
    useListeners,
    useProps,
  } from '@hooks';

  import fieldConfig from '../field-config';

  import AgentStatus from './components/AgentStatus.vue';
  import City from './components/City.vue';
  import Cpu from './components/Cpu.vue';
  import DeviceClass from './components/DeviceClass.vue';
  import Disk from './components/Disk.vue';
  import DiskType from './components/DiskType.vue';
  import ForBizs from './components/ForBizs.vue';
  import Hosts from './components/Hosts.vue';
  import Mem from './components/Mem.vue';
  import MountPoint from './components/MountPoint.vue';
  import ResourceTypes from './components/ResourceTypes.vue';
  import Subzones from './components/Subzones.vue';

  interface Props {
    name: string,
    model: Record<string, any>
  }
  interface Emits {
    (e: 'change', name: string, value: any): void
  }
  interface Expose {
    getValue: () => Promise<boolean>,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const inhertProps = useProps();
  const listeners = useListeners();
  const errorMessage = ref('');

  const comMap = {
    for_bizs: ForBizs,
    resource_types: ResourceTypes,
    hosts: Hosts,
    agent_status: AgentStatus,
    city: City,
    device_class: DeviceClass,
    mount_point: MountPoint,
    cpu: Cpu,
    mem: Mem,
    disk: Disk,
    disk_type: DiskType,
    subzones: Subzones,
  };

  const config = fieldConfig[props.name];

  const styles = {
    flex: config.flex ? config.flex : 1,
  };

  const renderCom = comMap[props.name as keyof typeof comMap];

  const handleChange = (value: any) => {
    errorMessage.value = '';
    emits('change', props.name, value);
  };

  defineExpose<Expose>({
    getValue() {
      if (!config.validator) {
        return Promise.resolve(true);
      }
      const result = config.validator(props.model[props.name]);
      console.log('getValuegetValuegetValue = ', props.name, props.model[props.name], result);
      if (_.isString(result)) {
        errorMessage.value = result;
        return Promise.reject(false);
      }

      errorMessage.value = '';
      return Promise.resolve(true);
    },
  });
</script>
<style lang="less">
  .resourece-pool-serach-item {
    display: inline-block;

    & ~ .resourece-pool-serach-item {
      .wrapper {
        margin-left: 40px;
      }
    }

    .wrapper{
      position: relative;
    }

    .search-item-label {
      margin-bottom: 6px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    .search-item-error{
      position: absolute;
      right: 0;
      bottom: -16px;
      left: 0;
      font-size: 12px;
      color: #ea3636;
    }
  }

  .resourece-pool-serach-item-action{
    display: flex;
    flex: 1;

    .action-item{
      flex: 1;
      text-align: center;
      cursor: pointer;

      & ~ .action-item{
        border-left: 1px solid #dcdee5;
      }
    }
  }
</style>
