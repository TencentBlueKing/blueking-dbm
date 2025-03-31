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
  <div class="capacity-form">
    <div class="spec-box mb-24">
      <div class="spec-box-item">
        <div class="spec-box-item-label">{{ t('当前规格') }} :</div>
        <div>{{ clusterData.mongodb[0].spec_config.name || '--' }}</div>
      </div>
      <div class="spec-box-item">
        <div class="spec-box-item-label">{{ t('变更后规格') }} :</div>
        <div>{{ specData?.spec_name ? `${specData?.spec_name}` : t('请先选择部署方案') }}</div>
      </div>
    </div>
    <div class="plan-title mb-16">{{ t('集群部署方案') }}</div>
    <DbForm
      ref="formRef"
      class="plan-form"
      :model="formData"
      :rules="rules">
      <ApplySchema
        v-model="applySchema"
        @change="handleApplySchemaChange" />
      <template v-if="applySchema === APPLY_SCHEME.AUTO">
        <BkFormItem
          :label="t('集群容量需求')"
          property="capacity"
          required>
          <BkInput
            v-model="formData.capacity"
            :min="0"
            style="width: 314px"
            type="number"
            @change="handleCapacityChange" />
          <span class="input-desc">G</span>
        </BkFormItem>
        <BkFormItem
          ref="specRef"
          label=""
          :label-width="0"
          property="spec_id"
          required>
          <DbOriginalTable
            v-bk-loading="{ loading: isLoading }"
            class="custom-edit-table"
            :data="specList"
            @row-click="handleRowClick">
            <BkTableColumn
              field="spec_name"
              fixed="left">
              <template #header>
                <BkPopover
                  ext-cls="mongo-config-spec-name-popover"
                  theme="light">
                  <span class="spec-name-head">{{ t('资源规格') }}</span>
                  <template #content>
                    <img
                      :src="SpecTip"
                      :width="200" />
                  </template>
                </BkPopover>
              </template>
              <template #default="{ data, index }: { data: MongoConfigSpecRow, index: number }">
                <div class="spec-id-box">
                  <BkRadio
                    :key="index"
                    v-model="formData.spec_id"
                    class="spec-radio"
                    :label="data.spec_id"
                    @click="(event: Event) => handleRowClick(event, data)">
                    <div
                      v-overflow-tips
                      class="text-overflow"
                      @click="(event: Event) => event.stopPropagation()">
                      {{ data.spec_name }}
                    </div>
                  </BkRadio>
                  <MiniTag
                    v-if="originSpecId === data.spec_id"
                    class="ml-2"
                    :content="t('当前方案')"
                    theme="info" />
                  <MiniTag
                    v-if="data.machine_num > data.count"
                    class="ml-2"
                    :content="t('资源不足')"
                    theme="danger" />
                </div>
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="shard_node_num"
              :label="t('每个Shard节点数')"
              :width="130">
            </BkTableColumn>
            <BkTableColumn
              field="shard_num"
              :label="t('Shard数量')">
            </BkTableColumn>
            <BkTableColumn
              field="shard_node_spec"
              :label="t('Shard节点规格')">
              <template #default="{ data }: { data: MongoConfigSpecRow }">
                <span>
                  {{
                    data.shard_choices.find((choiceItem) => choiceItem.shard_num === data.shard_num)?.shard_spec || '--'
                  }}
                </span>
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="machine_pair"
              :label="t('所需机组数')"
              :width="96">
            </BkTableColumn>
            <BkTableColumn
              field="machine_num"
              :label="t('所需机器数')"
              :width="96">
            </BkTableColumn>
            <BkTableColumn
              field="count"
              :label="t('可用主机数')"
              :width="96">
            </BkTableColumn>
            <template #empty>
              <p
                v-if="!formData.capacity"
                style="width: 100%; line-height: 128px; text-align: center">
                <DbIcon
                  class="mr-4"
                  type="attention" />
                <span>{{ t('请先设置容量') }}</span>
              </p>
              <BkException
                v-else
                :description="t('无匹配的资源规格_请先修改容量设置')"
                scene="part"
                style="font-size: 12px"
                type="empty" />
            </template>
          </DbOriginalTable>
        </BkFormItem>
      </template>

      <template v-if="applySchema === APPLY_SCHEME.CUSTOM">
        <BkFormItem
          :label="t('规格')"
          property="spec_id"
          required>
          <SpecSelector
            ref="specSelectorRef"
            v-model="formData.spec_id"
            :biz-id="clusterData.bk_biz_id"
            :cloud-id="clusterData.bk_cloud_id"
            :cluster-type="ClusterTypes.MONGODB"
            :machine-type="MachineTypes.MONGODB"
            style="width: 314px"
            @update:model-value="handleSpecChange" />
        </BkFormItem>
        <BkFormItem
          :label="t('每个 Shard 节点数')"
          property="shard_node_count"
          required>
          <BkInput
            v-model="formData.shard_node_count"
            :disabled="inputDisabled"
            :min="0"
            style="width: 314px"
            type="number" />
        </BkFormItem>
        <BkFormItem
          :label="t('集群 Shared 数')"
          property="shards_num"
          required>
          <BkInput
            v-model="formData.shards_num"
            :disabled="inputDisabled"
            :min="0"
            style="width: 314px"
            type="number" />
        </BkFormItem>
        <BkFormItem
          :label="t('机器组数')"
          property="shard_machine_group"
          required>
          <BkInput
            v-model="formData.shard_machine_group"
            :disabled="inputDisabled"
            :min="0"
            style="width: 314px"
            type="number" />
          <span class="input-desc">{{ t('组') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="t('每组机器 Shared 数')"
          property="machine_group_shard_num">
          <BkInput
            v-if="formData.machine_group_shard_num === 0"
            disabled
            :placeholder="t('自动生成')"
            style="width: 314px"
            type="number" />
          <BkInput
            v-else
            v-model="formData.machine_group_shard_num"
            disabled
            :placeholder="t('自动生成')"
            style="width: 314px"
            type="number" />
        </BkFormItem>
        <BkFormItem :label="t('总机器数')">
          <BkInput
            v-if="formData.count === 0"
            disabled
            :placeholder="t('自动生成')"
            style="width: 314px"
            type="number" />
          <BkInput
            v-else
            v-model="formData.count"
            disabled
            :placeholder="t('自动生成')"
            style="width: 314px"
            type="number" />
          <span class="input-desc">{{ t('台') }}</span>
        </BkFormItem>
      </template>
    </DbForm>
  </div>
</template>

<script setup lang="tsx">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { ClusterTypes, DBTypes, MachineTypes } from '@common/const';

  import MiniTag from '@components/mini-tag/index.vue';

  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import ApplySchema, { APPLY_SCHEME } from '@views/db-manage/common/apply-schema/Index.vue';

  import SpecTip from '@images/spec-tip.png';

  type MongoConfigSpecRow = {
    count: number;
    machine_num: number;
    shard_node_num: number;
    shard_node_spec: string;
    shard_num: number;
  } & ClusterSpecModel;

  interface Props {
    clusterData: {
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_name: string;
      cluster_type: string;
      id: number;
      mongodb: {
        spec_config: {
          id: number;
          name: string;
        };
      }[];
      shard_node_count: number;
      shard_num: number;
    };
  }

  type Emits = (e: 'confirm', inputInfo: UnwrapRef<typeof formData>, specInfo: UnwrapRef<typeof specData>) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isChange = defineModel<boolean>('isChange', { required: true });

  const { t } = useI18n();

  const getDefaultFormData = () => {
    if (props.clusterData.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER) {
      return {
        capacity: 0,
        count: 0,
        machine_group_shard_num: 0,
        shard_machine_group: 0,
        shard_node_count: 3,
        shards_num: 0,
        spec_id: props.clusterData.mongodb[0].spec_config.id,
      };
    }
    return {
      capacity: 0,
      count: props.clusterData.shard_node_count * 1,
      machine_group_shard_num: 1,
      shard_machine_group: 1,
      shard_node_count: props.clusterData.shard_node_count,
      shards_num: 1,
      spec_id: props.clusterData.mongodb[0].spec_config.id,
    };
  };

  const formRef = useTemplateRef('formRef');
  const specRef = useTemplateRef('specRef');
  const specSelectorRef = useTemplateRef('specSelectorRef');

  const applySchema = ref(APPLY_SCHEME.AUTO);

  const specData = shallowRef<
    {
      shard_recommend?: {
        shard_num: number;
        shard_spec: string;
      };
    } & Pick<ClusterSpecModel, 'cpu' | 'mem' | 'spec_name' | 'storage_spec' | 'qps'>
  >();
  const specList = shallowRef<MongoConfigSpecRow[]>([]);

  const formData = reactive(getDefaultFormData());

  let timer = 0;

  const rules = {
    capacity: [
      {
        message: t('集群容量需求不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    machine_group_shard_num: [
      {
        message: t('集群 Shared 数 / 机器组数，需要整除'),
        trigger: 'change',
        validator: () => {
          const { shard_machine_group: shardMachineGroup, shards_num: shardsNum } = formData;
          if (shardMachineGroup && shardsNum) {
            return shardsNum % shardMachineGroup === 0;
          }
          return true;
        },
      },
    ],
    shard_machine_group: [
      {
        message: t('机器组数不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    shard_node_count: [
      {
        message: t('每个 Shard 节点数不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    shards_num: [
      {
        message: t('集群 Shared 数不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    spec_id: [
      {
        message: t('规格不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
  };

  const originSpecId = computed(() => props.clusterData.mongodb[0].spec_config.id);
  const inputDisabled = computed(() => props.clusterData.cluster_type === ClusterTypes.MONGO_REPLICA_SET);

  const { loading: isLoading, run: getFilterClusterSpecRun } = useRequest(getFilterClusterSpec, {
    manual: true,
    onError() {
      specList.value = [];
    },
    onSuccess(res) {
      specList.value = res.map((item) =>
        Object.assign(item, {
          count: 0,
          machine_num: item.machine_pair * props.clusterData.shard_node_count, // 机器组数 x 每个Shard节点数
          shard_node_num: props.clusterData.shard_node_count,
          shard_node_spec: '',
          shard_num: item.shard_recommend.shard_num,
        }),
      );
      getSpecResourceCountRun({
        bk_biz_id: Number(props.clusterData.bk_biz_id),
        bk_cloud_id: props.clusterData.bk_cloud_id,
        spec_ids: specList.value.map((item) => item.spec_id),
      });
    },
  });

  const { run: getSpecResourceCountRun } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value = specList.value.map((item) =>
        Object.assign(item, {
          count: data[item.spec_id] ?? 0,
        }),
      );
    },
  });

  watch(
    () => formData.spec_id,
    (newSpecId) => {
      isChange.value = newSpecId > 0;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => formData.spec_id,
    (newSpecId) => {
      if (newSpecId) {
        specRef.value?.clearValidate();
      }
    },
  );

  watch(
    () => formData.capacity,
    (newCapacity) => {
      if (!newCapacity) {
        specList.value = [];
      } else {
        clearTimeout(timer);
        timer = setTimeout(() => {
          fetchFilterClusterSpec();
        }, 400);
      }
    },
  );

  watch(
    () => [formData.shard_node_count, formData.shard_machine_group],
    () => {
      formData.count = formData.shard_node_count * formData.shard_machine_group;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [formData.shards_num, formData.shard_machine_group],
    () => {
      if (formData.shards_num && formData.shard_machine_group) {
        formData.machine_group_shard_num = formData.shards_num / formData.shard_machine_group;
      } else {
        formData.machine_group_shard_num = 0;
      }
    },
    {
      immediate: true,
    },
  );

  const handleApplySchemaChange = () => {
    Object.assign(formData, getDefaultFormData());
  };

  const handleCapacityChange = () => {
    Object.assign(formData, {
      ...getDefaultFormData(),
      capacity: formData.capacity,
    });
    specData.value = undefined;
    specList.value = [];
  };

  const fetchFilterClusterSpec = () => {
    const { capacity } = formData;

    if (!capacity) {
      return;
    }

    getFilterClusterSpecRun({
      capacity: Number(formData.capacity),
      shard_num: props.clusterData.shard_num,
      spec_cluster_type: DBTypes.MONGODB,
      spec_machine_type: MachineTypes.MONGODB,
    });
  };
  fetchFilterClusterSpec();

  const handleRowClick = (event: Event, row: MongoConfigSpecRow) => {
    Object.assign(formData, {
      count: row.machine_num,
      shard_machine_group: row.machine_pair,
      shard_node_count: row.shard_node_num,
      shards_num: row.shard_num,
      spec_id: row.spec_id,
    });
    specData.value = row;
  };

  const handleSpecChange = () => {
    nextTick(() => {
      specData.value = specSelectorRef.value?.getData();
    });
  };

  defineExpose({
    cancel() {
      isChange.value = false;
    },
    submit() {
      return formRef.value!.validate().then(() => {
        emits('confirm', formData, specData.value);
        return Promise.resolve(true);
      });
    },
  });
</script>

<style lang="less" scoped>
  .capacity-form {
    padding: 28px 40px 24px;

    .spec-box {
      display: flex;
      flex-wrap: wrap;
      padding: 12px 16px;
      font-size: 12px;
      background-color: #fafbfd;

      .spec-box-item {
        display: flex;
        width: 50%;
        line-height: 22px;

        .spec-box-item-label {
          min-width: 100px;
          padding-right: 8px;
          text-align: right;
        }
      }
    }

    .plan-title {
      font-size: 12px;
      font-weight: bolder;
      color: #313238;
    }

    .plan-form {
      :deep(.bk-form-label) {
        font-size: 12px;
        color: #63656e;
      }

      .input-desc {
        padding-left: 12px;
        font-size: 12px;
        line-height: 20px;
        color: #63656e;
      }
    }

    .tips {
      display: flex;
      align-items: center;
      font-size: 12px;
    }
  }
</style>
