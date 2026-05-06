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
    :label="t('最终容量')"
    :min-width="400"
    readonly>
    <EditableBlock :placeholder="t('选择集群后自动生成')">
      <ShardChangeCapacityCell
        v-if="cluster.id"
        v-model="modelValue"
        :cluster="cluster"
        :diff-group-num="addGroupNum"
        type="target" />
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import ShardChangeCapacityCell from '@views/db-manage/redis/common/toolbox-field/ShardChangeCapacityCell.vue';

  interface Props {
    addGroupNum: number;
    cluster: {
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      id: number;
      machine_pair_cnt: number;
    };
  }

  defineProps<Props>();

  const modelValue = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();
</script>
