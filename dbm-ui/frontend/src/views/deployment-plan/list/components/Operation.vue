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
  <div class="deployment-plan-operation-box">
    <DbForm
      form-type="vertical"
      :model="formData">
      <DbFormItem
        :label="t('方案名称')"
        required>
        <BkInput
          v-model="formData.name"
          :maxlength="15"
          placeholder="推荐名称方式：总容量（分片大小 x  分片数），如：1500G (37.5G x 40分片）"
          :readonly="isEditing" />
      </DbFormItem>
      <DbFormItem
        :label="t('集群分片数量')"
        property="shard_cnt"
        required>
        <BkInput
          v-model="formData.shard_cnt"
          :readonly="isEditing"
          type="number" />
      </DbFormItem>
      <div class="row">
        <div class="col">
          <DbFormItem
            :label="t('后端存储资源规格')"
            property="spec"
            required>
            <BkSelect
              v-model="formData.spec"
              :disabled="isEditing"
              :loading="isResourceSpecLoading">
              <BkOption
                v-for="item in resourceSpecList?.results"
                :key="item.spec_id"
                :label="item.spec_name"
                :value="item.spec_id" />
            </BkSelect>
          </DbFormItem>
        </div>
        <div class="col">
          <DbFormItem
            :label="t('机器组数（每组 2 台）')"
            property="machine_pair_cnt"
            required>
            <BkInput
              v-model="formData.machine_pair_cnt"
              :readonly="isEditing"
              type="number" />
          </DbFormItem>
        </div>
      </div>
    </DbForm>
    <div
      v-if="estimateCapacity"
      class="disk-box">
      集群预估容量：
      <span class="number-strong">{{ estimateCapacity }}G</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    reactive,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createDeployPlan } from '@services/dbResource';
  import type DeployPlanModel from '@services/model/db-resource/DeployPlan';
  import { getResourceSpecList } from '@services/resourceSpec';

  interface Props {
    clusterType: string,
    machineType: string,
    data?: DeployPlanModel
  }

  interface Emits{
    (e: 'change'): void
  }

  interface Expose {
    submit: () => void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const genDefaultData = () => ({
    id: 0,
    name: '',
    shard_cnt: 0,
    capacity: 0,
    machine_pair_cnt: 0,
    cluster_type: props.clusterType,
    desc: '',
    spec: undefined,
  });
  const { t } = useI18n();

  const formData = reactive(genDefaultData());
  const isEditing = computed(() => props.data && props.data.id > 0);

  const {
    loading: isResourceSpecLoading,
    data: resourceSpecList,
  } = useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: props.clusterType,
        spec_machine_type: props.machineType,
      },
    ],
  });

  const estimateCapacity = computed(() => {
    if (formData.machine_pair_cnt < 1) {
      return '';
    }
    const spec = _.find(resourceSpecList.value?.results, item => item.spec_id === formData.spec);
    if (!spec) {
      return '';
    }
    // tendiscache 计算内存
    if (props.machineType === 'tendiscache') {
      const { min, max } = spec.mem;
      return `${min * formData.machine_pair_cnt} - ${max * formData.machine_pair_cnt}`;
    }
    const storage = spec.storage_spec.reduce((result, item) => result + item.size, 0);
    return `>= ${storage * formData.machine_pair_cnt}`;
  });

  watch(() => props.data, () => {
    if (!props.data) {
      return;
    }
    formData.id = props.data.id;
    formData.name = props.data.name;
    formData.shard_cnt = props.data.shard_cnt;
    formData.machine_pair_cnt = props.data.machine_pair_cnt;
    formData.capacity = props.data.capacity;
  },  {
    immediate: true,
  });


  defineExpose<Expose>({
    submit() {
      return createDeployPlan({
        ...formData,
        capacity: estimateCapacity.value,
      })
        .then(() => emits('change'));
    },
  });

</script>
<style lang="less">
  .deployment-plan-operation-box {
    padding: 24px 40px;

    .row {
      display: flex;

      & ~ .row {
        margin-top: 24px;
      }
    }

    .col {
      flex: 1;

      & ~ .col {
        margin-left: 40px;
      }
    }

    .disk-box {
      display: flex;
      height: 50px;
      padding: 0 16px;
      margin-top: 24px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;
      align-items: center;

      .number-strong {
        font-weight: bold;
        color: #63656e;
      }
    }
  }
</style>
