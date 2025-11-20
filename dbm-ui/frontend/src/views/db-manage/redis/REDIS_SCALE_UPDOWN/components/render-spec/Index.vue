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
  <div class="render-spec-box">
    {{ displayInfo.name }}
    <SpecDetailPopover :data="displayInfo">
      <DbIcon
        class="visible-icon ml-4"
        type="visible1" />
    </SpecDetailPopover>
  </div>
</template>
<script setup lang="ts">
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  interface Props {
    data: {
      count?: number;
      cpu?: {
        max: number;
        min: number;
      };
      id?: number;
      mem?: {
        max: number;
        min: number;
      };
      name?: string;
      qps?: {
        max: number;
        min: number;
      };
      spec_id?: number;
      spec_name?: string;
      storage_spec?: {
        max: number;
        min: number;
        mount_point: string;
        size?: number;
        type: string;
      }[];
    };
  }

  const props = defineProps<Props>();

  const displayInfo = computed(() =>
    Object.assign(
      {
        // count: 0,
        cpu: {
          max: 1,
          min: 0,
        },
        // id: 0,
        mem: {
          max: 1,
          min: 0,
        },
        name: '',
        qps: {
          max: 1,
          min: 0,
        },
        spec_id: 0,
        spec_name: '',
        storage_spec: [],
      },
      props.data,
      {
        // id: props.data?.id || (props.data?.spec_id as number),
        name: props.data?.name || (props.data?.spec_name as string),
      },
    ),
  );
</script>
<style lang="less" scoped>
  .render-spec-box {
    overflow: hidden;
    line-height: 20px;
    color: #313238;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }

  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
