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
  <RenderText
    class="old-master-slave-host"
    :data="data.join(',')"
    :is-loading="loading"
    :placeholder="t('选择集群后自动生成')">
    <template #content>
      <div>
        <div class="host-item">
          <div class="host-tag host-tag-master">M</div>
          <div>{{ data[0] }}</div>
        </div>
        <div class="host-item mt-4">
          <div class="host-tag host-tag-slave">S</div>
          <div>{{ data[1] }}</div>
        </div>
      </div>
    </template>
  </RenderText>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    data?: string[];
    loading?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    data: () => [],
    loading: false,
  });

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .old-master-slave-host {
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
  }
</style>
