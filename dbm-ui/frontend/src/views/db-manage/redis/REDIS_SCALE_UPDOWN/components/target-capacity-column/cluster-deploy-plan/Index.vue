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
  <BkSideslider
    :before-close="handleBeforeClose"
    :is-show="isShow"
    :width="800"
    @closed="handleClose">
    <template #header>
      {{ title }}【{{ cluster.master_domain }}】<BkTag theme="info">{{ t('存储层') }}</BkTag>
    </template>
    <div class="redis-deploy-plan">
      <PreviewResult
        :cluster="cluster"
        :target-info="targetInfo"
        :update-info="updateInfo" />
      <div class="deploy-box">
        <div class="title-spot">{{ t('集群部署方案') }}<span class="required" /></div>
        <DbForm
          ref="formRef"
          class="mt-16"
          :model="targetInfo">
          <ApplySchema
            v-model="applySchema"
            @change="handleChange" />
          <AutoSchema
            v-if="applySchema === APPLY_SCHEME.AUTO"
            ref="autoSchemaRef"
            v-bind="props"
            @change="handleAutoUpdate" />
          <CustomSchema
            v-else
            v-model="targetInfo"
            v-bind="props"
            @change="handleCustomUpdate" />
        </DbForm>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="sumbitDisable"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type RedisModel from '@services/model/redis/redis';
  import type ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getRedisClusterCapacityUpdateInfo } from '@services/source/redisToolbox';

  import { useBeforeClose } from '@hooks';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import { messageError } from '@utils';

  import ApplySchema, { APPLY_SCHEME } from './components/ApplySchema.vue';
  import AutoSchema from './components/AutoSchema.vue';
  import CustomSchema from './components/CustomSchema.vue';
  import PreviewResult from './components/PreviewResult.vue';

  export type TargetInfo = ComponentProps<typeof PreviewResult>['targetInfo'];
  export type UpdateInfo = ServiceReturnType<typeof getRedisClusterCapacityUpdateInfo>;

  interface Props {
    cluster: RedisModel;
    dbVersion: string;
    type?: 'capacityChange' | 'typeChange'; // 容量变更、类型变更
  }

  type Emits = (
    e: 'change',
    data: {
      targetInfo: TargetInfo;
      updateInfo: UpdateInfo;
    },
  ) => void;

  const props = withDefaults(defineProps<Props>(), {
    type: 'capacityChange',
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const autoSchemaRef = ref<InstanceType<typeof AutoSchema>>();
  const formRef = ref();
  const applySchema = ref(APPLY_SCHEME.AUTO);
  const defaultTargetInfo = () => ({
    capacity: 0,
    clusterShardNum: 0,
    clusterStats: {
      in_use: 0,
      total: 0,
      used: 0,
    },
    groupNum: 0,
    shardNum: 0,
    spec: {
      cpu: {
        max: 1,
        min: 0,
      },
      mem: {
        max: 1,
        min: 0,
      },
      qps: {
        max: 1,
        min: 0,
      },
      spec_id: 0,
      spec_name: '',
      storage_spec: [] as ComponentProps<typeof RenderSpec>['data']['storage_spec'],
    },
  });
  const targetInfo = reactive<TargetInfo>(defaultTargetInfo());
  const defaultUpdateInfo = () => ({
    capacity_update_type: '',
    err_msg: '',
    old_machine_info: [],
    require_machine_group_num: 0,
    require_spec_id: 0,
  });
  const updateInfo = reactive<UpdateInfo>(defaultUpdateInfo());
  const sumbitDisable = ref(false);

  const title = computed(() => {
    if (props.type === 'typeChange') {
      return t('选择集群类型变更部署方案');
    }
    return t('选择集群容量变更部署方案');
  });

  const handleChange = () => {
    Object.assign(targetInfo, defaultTargetInfo());
    Object.assign(updateInfo, defaultUpdateInfo());
    sumbitDisable.value = false;
  };

  const handleAutoUpdate = (row: ClusterSpecModel) => {
    getRedisClusterCapacityUpdateInfo({
      cluster_id: props.cluster.id!,
      new_machine_group_num: row.machine_pair,
      new_shards_num: row.cluster_shard_num,
      new_spec_id: row.spec_id,
      new_storage_version: props.dbVersion!,
    }).then((data) => {
      if (data.err_msg) {
        sumbitDisable.value = true;
        messageError(data.err_msg);
        autoSchemaRef.value?.disable(row.spec_id);
        return;
      }
      sumbitDisable.value = false;
      autoSchemaRef.value?.choose(row.spec_id);
      Object.assign(targetInfo, {
        capacity: row.cluster_capacity,
        clusterStats: props.cluster.cluster_stats,
        groupNum: row.machine_pair,
        shardNum: row.cluster_shard_num,
        spec: {
          cpu: row.cpu,
          mem: row.mem,
          qps: row.qps,
          spec_id: row.spec_id,
          spec_name: row.spec_name,
          storage_spec: row.storage_spec,
        },
      });
      Object.assign(updateInfo, data);
    });
  };

  const handleCustomUpdate = (payload: TargetInfo) => {
    getRedisClusterCapacityUpdateInfo({
      cluster_id: props.cluster.id!,
      new_machine_group_num: payload.groupNum,
      new_shards_num: payload.shardNum,
      new_spec_id: Number(payload.spec.spec_id),
      new_storage_version: props.dbVersion!,
    }).then((data) => {
      if (data.err_msg) {
        sumbitDisable.value = true;
        messageError(data.err_msg);
        return;
      }
      sumbitDisable.value = false;
      Object.assign(targetInfo, payload);
      Object.assign(updateInfo, data);
    });
  };

  const handleClose = async () => {
    const result = await handleBeforeClose();
    if (!result) {
      return;
    }
    window.changeConfirm = false;
    isShow.value = false;
  };

  const handleConfirm = async () => {
    const result = await formRef.value.validate();
    if (!result) {
      return;
    }
    emits('change', {
      targetInfo,
      updateInfo,
    });
    window.changeConfirm = true;
    isShow.value = false;
  };
</script>
<style lang="less">
  .redis-deploy-plan {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

    .deploy-box {
      margin-top: 24px;

      .input-box {
        display: flex;
        align-items: center;

        .uint-text {
          font-size: 12px;

          .spec-text {
            margin: 0 2px;
            font-weight: 700;
          }
        }
      }

      .deploy-table {
        margin-top: 12px;

        :deep(.cluster-name) {
          padding: 8px 0;
          line-height: 16px;

          &__alias {
            color: @light-gray;
          }
        }

        :deep(.bk-form-label) {
          display: none;
        }

        :deep(.bk-form-error-tips) {
          top: 50%;
          transform: translateY(-50%);
        }

        :deep(.regex-input) {
          margin: 8px 0;
        }
      }
    }
  }
</style>
