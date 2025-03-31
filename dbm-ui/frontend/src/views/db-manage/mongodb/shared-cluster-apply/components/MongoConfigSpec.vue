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
  <div class="mongo-config-spec">
    <ApplySchema
      v-model="applySchema"
      @change="handleApplySchemaChange" />
    <template v-if="applySchema === APPLY_SCHEME.AUTO">
      <BkFormItem
        :label="t('集群容量需求')"
        property="details.resource_spec.mongodb.capacity"
        required>
        <BkInput
          v-model="modelValue.capacity"
          :min="0"
          style="width: 314px"
          type="number"
          @change="handleCapacityChange" />
        <span class="input-desc">G</span>
      </BkFormItem>
      <BkFormItem
        ref="specRef"
        :label="t('集群部署方案')"
        property="details.resource_spec.mongodb.spec_id"
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
                  v-model="modelValue.spec_id"
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
            <template #default="{ data }: { data: MongoConfigSpecRow }">
              <BkSelect
                v-model="data.shard_num"
                class="shard-node-spec"
                :clearable="false"
                @change="handleShardNumChange">
                <BkOption
                  v-for="(choiceItem, choiceIndex) in data.shard_choices"
                  :key="choiceIndex"
                  :label="choiceItem.shard_num"
                  :value="choiceItem.shard_num" />
              </BkSelect>
            </template>
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
              v-if="!modelValue.capacity"
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
        property="details.resource_spec.mongodb.spec_id"
        required>
        <SpecSelector
          ref="specSelectorRef"
          v-model="modelValue.spec_id"
          :biz-id="params.bk_biz_id"
          :cloud-id="params.bk_cloud_id"
          :cluster-type="ClusterTypes.MONGODB"
          :machine-type="MachineTypes.MONGODB"
          style="width: 314px"
          @update:model-value="handleSpecChange" />
      </BkFormItem>
      <BkFormItem
        :label="t('每个 Shard 节点数')"
        property="details.resource_spec.mongodb.shard_node_count"
        required>
        <BkInput
          v-model="modelValue.shard_node_count"
          :min="0"
          style="width: 314px"
          type="number" />
      </BkFormItem>
      <BkFormItem
        :label="t('集群 Shared 数')"
        property="details.resource_spec.mongodb.shards_num"
        required>
        <BkInput
          v-model="modelValue.shards_num"
          :min="0"
          style="width: 314px"
          type="number" />
      </BkFormItem>
      <BkFormItem
        :label="t('机器组数')"
        property="details.resource_spec.mongodb.shard_machine_group"
        required>
        <BkInput
          v-model="modelValue.shard_machine_group"
          :min="0"
          style="width: 314px"
          type="number" />
        <span class="input-desc">{{ t('组') }}</span>
      </BkFormItem>
      <BkFormItem
        :label="t('每组机器 Shared 数')"
        property="details.resource_spec.mongodb.machine_group_shard_num">
        <BkInput
          v-if="modelValue.machine_group_shard_num === 0"
          disabled
          :placeholder="t('自动生成')"
          style="width: 314px"
          type="number" />
        <BkInput
          v-else
          v-model="modelValue.machine_group_shard_num"
          disabled
          :placeholder="t('自动生成')"
          style="width: 314px"
          type="number" />
      </BkFormItem>
      <BkFormItem :label="t('总机器数')">
        <BkInput
          v-if="modelValue.count === 0"
          disabled
          :placeholder="t('自动生成')"
          style="width: 314px"
          type="number" />
        <BkInput
          v-else
          v-model="modelValue.count"
          disabled
          :placeholder="t('自动生成')"
          style="width: 314px"
          type="number" />
        <span class="input-desc">{{ t('台') }}</span>
      </BkFormItem>
    </template>
  </div>
</template>

<script setup lang="tsx">
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
    params: {
      bk_biz_id: number | '';
      bk_cloud_id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    capacity: number;
    count: number;
    machine_group_shard_num: number;
    shard_machine_group: number;
    shard_node_count: number;
    shards_num: number;
    spec_id: number;
  }>({
    required: true,
  });

  const applySchema = defineModel<APPLY_SCHEME>('applySchema', { required: true });

  const specData =
    defineModel<Pick<ClusterSpecModel, 'cpu' | 'instance_num' | 'mem' | 'spec_name' | 'storage_spec'>>('specData');

  const { t } = useI18n();

  const specRef = useTemplateRef('specRef');
  const specSelectorRef = useTemplateRef('specSelectorRef');

  const specList = ref<MongoConfigSpecRow[]>([]);

  let timer = 0;

  const { loading: isLoading, run: getFilterClusterSpecRun } = useRequest(getFilterClusterSpec, {
    manual: true,
    onError() {
      specList.value = [];
    },
    onSuccess(res) {
      specList.value = res.map((item) =>
        Object.assign(item, {
          count: 0,
          machine_num: item.machine_pair * 3, // 机器组数 x 每个Shard节点数
          shard_node_num: 3,
          shard_node_spec: '',
          shard_num: item.shard_recommend.shard_num,
        }),
      );
      getSpecResourceCountRun({
        bk_biz_id: Number(props.params.bk_biz_id),
        bk_cloud_id: props.params.bk_cloud_id,
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
    () => modelValue.value.spec_id,
    (newSpecId) => {
      if (newSpecId) {
        specRef.value?.clearValidate();
      }
    },
  );

  watch(
    () => modelValue.value.capacity,
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
    () => [modelValue.value.shard_node_count, modelValue.value.shard_machine_group],
    () => {
      modelValue.value.count = modelValue.value.shard_node_count * modelValue.value.shard_machine_group;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [modelValue.value.shards_num, modelValue.value.shard_machine_group],
    () => {
      if (modelValue.value.shards_num && modelValue.value.shard_machine_group) {
        modelValue.value.machine_group_shard_num = modelValue.value.shards_num / modelValue.value.shard_machine_group;
      } else {
        modelValue.value.machine_group_shard_num = 0;
      }
    },
    {
      immediate: true,
    },
  );

  const handleApplySchemaChange = () => {
    Object.assign(modelValue.value, {
      capacity: 0,
      count: 0,
      machine_group_shard_num: 0,
      shard_machine_group: 0,
      shard_node_count: 3,
      shards_num: 0,
      spec_id: 0,
    });
  };

  const handleCapacityChange = () => {
    Object.assign(modelValue.value, {
      count: 0,
      machine_group_shard_num: 0,
      shard_machine_group: 0,
      shard_node_count: 3,
      shards_num: 0,
      spec_id: 0,
    });
    specData.value = undefined;
    specList.value = [];
  };

  const handleShardNumChange = (value: number) => {
    modelValue.value.shards_num = value;
  };

  const fetchFilterClusterSpec = () => {
    const { capacity } = modelValue.value;

    if (!capacity) {
      return;
    }

    getFilterClusterSpecRun({
      capacity: Number(modelValue.value.capacity),
      spec_cluster_type: DBTypes.MONGODB,
      spec_machine_type: MachineTypes.MONGODB,
    });
  };
  fetchFilterClusterSpec();

  const handleRowClick = (event: Event, row: MongoConfigSpecRow) => {
    Object.assign(modelValue.value, {
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
</script>

<style lang="less" scoped>
  .mongo-config-spec {
    max-width: 1200px;
    padding: 24px 24px 24px 0;
    background-color: #f5f7fa;
    border-radius: 2px;

    .capacity-label {
      :deep(.bk-form-label) {
        font-weight: 700;
      }
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }
  }
</style>

<style>
  .mongo-config-spec-name-popover {
    padding: 16px !important;
  }
</style>
