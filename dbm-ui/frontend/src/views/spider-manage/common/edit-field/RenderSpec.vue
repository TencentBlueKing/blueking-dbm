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
  <BkLoading :loading="isLoading">
    <SpecPanel
      :data="data"
      hide-qps
      :is-show="isShowPopover">
      <div
        class="render-spec-box"
        :class="{'default-display': !isDisplay}"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave">
        <span
          v-if="!isDisplay"
          style="color: #c4c6cc;">
          {{ $t('输入主机后自动生成') }}
        </span>
        <span
          v-else
          class="content">
          {{ isDisplay ? `${data?.name} ${$t('((n))台', {n: data?.count})}` : '' }}
        </span>
      </div>
    </SpecPanel>
  </BkLoading>
</template>
<script setup lang="ts">
  import SpecPanel from '@views/spider-manage/common/spec-panel/Index.vue';

  interface Props {
    data?: {
      name: string;
      cpu: {
        max: number;
        min: number;
      },
      id: number;
      mem: {
        max: number;
        min: number;
      },
      qps: {
        max: number;
        min: number;
      }
      storage_spec: {
        mount_point: string;
        size: number;
        type: string;
      }[],
      count?: number;
    };
    isLoading?: boolean;
  }

  const props = defineProps<Props>();
  const isShowPopover = ref(false);
  const isDisplay = computed(() => props.data?.name && props.data.count !== undefined && props.data.count > 0);
  let timer = 0;

  const handleMouseEnter = () => {
    timer = setTimeout(() => {
      if (props.data) {
        isShowPopover.value = true;
      }
    }, 500);
  };

  const handleMouseLeave = () => {
    clearTimeout(timer);
    isShowPopover.value = false;
  };

</script>
<style lang="less" scoped>
.render-spec-box {
  height: 42px;
  padding: 10px 16px;
  overflow: hidden;
  line-height: 20px;
  color: #63656e;
  text-overflow:ellipsis;
  white-space: nowrap;

  .content {
    padding-bottom: 2px;
    cursor: pointer;
    border-bottom: 1px dotted #979BA5;
  }
}

.default-display {
  cursor: not-allowed;
  background: #FAFBFD;
}
</style>
