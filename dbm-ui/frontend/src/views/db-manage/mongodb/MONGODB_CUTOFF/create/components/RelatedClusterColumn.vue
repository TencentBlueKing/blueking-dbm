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
  <EditableColumn
    ref="editableTableColumn"
    field="host.master_domain"
    :label="t('所属集群')"
    :rowspan="rowspan"
    :width="200">
    <EditableBlock
      v-model="modelValue.domain"
      :placeholder="t('输入主机后自动生成')">
      <div>{{ modelValue.domain }}</div>
      <div
        v-if="modelValue.related_clusters.length > 0"
        class="related-clusters-main">
        <div class="item-info">— {{ t('同机关联集群') }}：</div>
        <div
          v-for="(item, index) in modelValue.related_clusters"
          :key="index">
          <div class="item-info">— {{ item.master_domain }}</div>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    rowspan?: number;
  }

  defineProps<Props>();

  const modelValue = defineModel<{
    domain: string;
    related_clusters: {
      master_domain: string;
    }[];
  }>({
    required: true,
  });

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .related-clusters-main {
    font-size: 12px;
    color: #979ba5;

    .item-info {
      height: 20px;
      line-height: 20px;
    }
  }
</style>
