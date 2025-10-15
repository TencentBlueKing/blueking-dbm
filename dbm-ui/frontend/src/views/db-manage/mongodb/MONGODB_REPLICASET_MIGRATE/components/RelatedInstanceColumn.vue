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
    :label="t('关联实例')"
    :min-width="300"
    readonly>
    <EditableBlock
      class="related-instance-column"
      :placeholder="t('选择集群后自动生成')">
      <div
        v-for="(item, index) in modelValue"
        :key="index">
        <div class="domain-item">{{ item.domain }}</div>
        <div
          v-for="(instance, instaneIndex) in item.instances"
          :key="instaneIndex"
          class="instance-item">
          --{{ instance }}
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  interface Props {
    clusters: Record<
      string,
      {
        mongodb: MongodbModel['mongodb'];
      }
    >;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<
    {
      domain: string;
      instances: string[];
    }[]
  >({
    required: true,
  });

  const { t } = useI18n();

  watch(
    () => props.clusters,
    () => {
      modelValue.value = Object.entries(props.clusters).map(([domain, clusterInfo]) => ({
        domain,
        instances: clusterInfo.mongodb.map((mongodbItem) => mongodbItem.instance),
      }));
    },
  );
</script>

<style lang="less" scoped>
  .related-instance-column {
    .domain-item {
      color: #4d4f56;
    }

    .instance-item {
      color: #979ba5;
    }
  }
</style>
