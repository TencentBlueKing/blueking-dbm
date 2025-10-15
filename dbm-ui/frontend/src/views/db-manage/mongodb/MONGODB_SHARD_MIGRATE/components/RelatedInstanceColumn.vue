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
    :label="t('关联集群')"
    readonly
    :width="350">
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-for="item in domainList"
        :key="item">
        {{ item }}
      </div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :label="t('关联集群实例')"
    :min-width="300"
    readonly>
    <EditableBlock
      class="related-instance-column"
      :placeholder="t('选择集群后自动生成')">
      <div
        v-for="(item, index) in dataList"
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

<script lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import ShardNameBatchColumn from './ShardNameBatchColumn.vue';

  interface Props {
    shards: ComponentProps<typeof ShardNameBatchColumn>['modelValue']['shards'];
  }

  export const getClusterInstanceList = (data: Props['shards']) => {
    const clusterInstanceMap = Object.values(data).reduce<Record<string, string[]>>((prev, shardItem) => {
      if (prev[shardItem.master_domain]) {
        return Object.assign(prev, {
          [shardItem.master_domain]: prev[shardItem.master_domain].concat(
            shardItem.related_instance.map((relatedInstanceItem) => relatedInstanceItem.instance),
          ),
        });
      }
      return Object.assign(prev, {
        [shardItem.master_domain]: shardItem.related_instance.map(
          (relatedInstanceItem) => relatedInstanceItem.instance,
        ),
      });
    }, {});
    return Object.entries(clusterInstanceMap).map(([domain, instance]) => ({
      domain,
      instances: _.uniq(instance),
    }));
  };
</script>

<script setup lang="ts">
  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList = computed(() => getClusterInstanceList(props.shards));

  const domainList = computed(() => _.uniq(dataList.value.map((dataItem) => dataItem.domain)));
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
