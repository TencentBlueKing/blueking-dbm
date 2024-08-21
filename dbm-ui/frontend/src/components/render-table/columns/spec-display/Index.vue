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
    <div
      class="render-spec-box"
      :class="{ 'default-display': !data }">
      <span
        v-if="!data"
        style="color: #c4c6cc">
        {{ placeholder || t('输入主机后自动生成') }}
      </span>
      <span
        v-else
        class="content">
        {{ data?.name ? `${data.name} ${isIgnoreCounts ? '' : t('((n))台', { n: data?.count })}` : '' }}
        <SpecPanel
          :data="data"
          :hide-qps="hideQps">
          <DbIcon
            class="visible-icon ml-4"
            type="visible1" />
        </SpecPanel>
      </span>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import SpecPanel from './Panel.vue';

  interface Props {
    data?: {
      name: string;
      cpu: {
        max: number;
        min: number;
      };
      id: number;
      mem: {
        max: number;
        min: number;
      };
      qps: {
        max: number;
        min: number;
      };
      storage_spec: {
        mount_point: string;
        size: number;
        type: string;
      }[];
      count?: number;
    };
    isLoading?: boolean;
    isIgnoreCounts?: boolean;
    placeholder?: string;
    hideQps?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    data: undefined,
    placeholder: undefined,
    isLoading: false,
    isIgnoreCounts: false,
    hideQps: true,
  });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .render-spec-box {
    height: 42px;
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .content {
      // padding-bottom: 2px;
      cursor: pointer;
      color: #313238;
      // border-bottom: 1px dotted #979ba5;
    }
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }

  .visible-icon {
    color: #3a84ff;
    cursor: pointer;
    font-size: 16px;
  }
</style>
