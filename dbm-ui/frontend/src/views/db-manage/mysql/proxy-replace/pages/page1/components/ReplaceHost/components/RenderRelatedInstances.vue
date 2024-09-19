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
    v-if="list.length"
    class="related-instances">
    <div
      v-for="(item, index) in list"
      :key="index"
      class="item">
      <span>{{ item.instance }}</span>
    </div>
  </div>
  <RenderText
    v-else
    :placeholder="t('自动生成')" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    list: {
      cluster_id: number;
      instance: string;
    }[];
  }

  interface Exposes {
    getValue: () => Promise<{ cluster_ids: number[] }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    list: () => [],
  });

  const { t } = useI18n();

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve({
        cluster_ids: (props.list || []).map((item) => item.cluster_id),
      });
    },
  });
</script>
<style lang="less">
  .related-instances {
    padding: 10px 16px;
    line-height: 20px;
    background: #fff;

    .item {
      width: 100%;
      overflow-x: hidden;
      text-overflow: ellipsis;
    }
  }
</style>
