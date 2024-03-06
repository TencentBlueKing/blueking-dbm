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
  <DbFormItem
    :label="t('构造新主机规格')"
    property="specId"
    required
    :rules="rules">
    <div class="mongo-dbstruct-target-spec">
      <RenderTargetSpec
        ref="specProxyRef"
        v-model="moduleValue"
        :biz-id="3"
        :cloud-id="0"
        :cluster-type="clusterType"
        machine-type="mongodb"
        :show-refresh="false" />
    </div>
  </DbFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongoDBModel from '@services/model/mongodb/mongodb';

  import RenderTargetSpec from '@components/apply-items/SpecSelector.vue';

  interface Props {
    data: MongoDBModel;
    clusterType: string;
    isShardCluster: boolean;
    shardNum: number;
    clusterIds: number[];
  }

  interface Exposes {
    getValue: () => any;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const moduleValue = defineModel<number | string>({
    default: '',
  });

  const rules = [
    {
      validator: (value: number) => value >= 0,
      message: t('目标集群不能为空'),
      trigger: 'change',
    },
  ];

  watch(() => props.clusterType, () => {
    moduleValue.value = '';
  });

  defineExpose<Exposes>({
    getValue() {
      const mongodbCount = props.isShardCluster
        ? Math.ceil(props.data.shard_num / props.shardNum)
        : Math.ceil(props.clusterIds.length / props.shardNum);
      const info = {
        resource_spec: {
          mongodb: {
            spec_id: moduleValue.value,
            count: mongodbCount,
          },
        },
      };
      if (props.isShardCluster) {
        Object.assign(info.resource_spec, {
          mongo_config: {
            spec_id: props.data.mongo_config[0].spec_config.id, // 这个与回档集群的mongo_config规格一致
            count: 1, // 固定为1
          },
          mongos: {
            spec_id: props.data.mongos[0].spec_config.id, // 这个与回档集群的mongos规格一致
            count: 1, // 固定为1
          },
        });
      }
      return info;
    },
  });
</script>
<style lang="less" scoped>
  .mongo-dbstruct-target-spec {
    :deep(.bk-input) {
      width: 400px;
    }
  }
</style>
