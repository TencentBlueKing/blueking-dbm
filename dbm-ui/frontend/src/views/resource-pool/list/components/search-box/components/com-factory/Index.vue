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
  <Component
    :is="renderCom"
    v-bind="attrs"
    v-on="listeners"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import { useAttrs } from 'vue';

  import { useListeners } from '@hooks';

  import AgentStatus from './AgentStatus.vue';
  import City from './City.vue';
  import Cpu from './Cpu.vue';
  import DeviceClass from './DeviceClass.vue';
  import Disk from './Disk.vue';
  import DiskType from './DiskType.vue';
  import ForBizs from './ForBizs.vue';
  import Hosts from './Hosts.vue';
  import Mem from './Mem.vue';
  import MountPoint from './MountPoint.vue';
  import ResourceTypes from './ResourceTypes.vue';
  import Subzones from './Subzones.vue';

  interface Props {
    name: string,
  }
  interface Emits {
    (e: 'change', value: string): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const attrs = useAttrs();
  const listeners = useListeners();

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

  const renderCom = comMap[props.name as keyof typeof comMap];

  const handleChange = (value: any) => {
    emits('change', props.name, value);
  };
</script>
