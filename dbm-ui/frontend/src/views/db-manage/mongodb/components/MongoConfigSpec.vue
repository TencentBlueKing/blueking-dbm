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
    class="mongo-config-spec"
    :class="{ 'mongo-config-spec-apply': isApply }">
    <BkFormItem
      :class="{ 'capacity-label': !isApply }"
      :label="t('集群容量需求')"
      :property="properties.capacity"
      required>
      <BkInput
        :min="0"
        :model-value="modelValue.capacity"
        style="width: 314px"
        type="number"
        @change="handleCapacityChange" />
      <span class="input-desc">G</span>
    </BkFormItem>
    <BkFormItem
      ref="specRef"
      :class="{ 'capacity-label': !isApply }"
      :label="t('集群部署方案')"
      :property="properties.specId"
      required>
      <DbOriginalTable
        v-bkloading="{ loading: isLoading }"
        class="custom-edit-table"
        :columns="columns"
        :data="specList"
        @row-click="handleRowClick">
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
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import {
    ClusterTypes,
    MachineTypes,
  } from '@common/const';

  import MiniTag from '@components/mini-tag/index.vue';

  import SpecTip from '@images/spec-tip.png';

  type RedisClusterSpecRow = ClusterSpecModel & {
    shard_node_num: number;
    shard_num: number;
    shard_node_spec: string;
    machine_num: number;
    count: number;
  }

  interface Props {
    properties: {
      capacity: string,
      specId: string,
    },
    bizId: number | string,
    cloudId: number | string,
    shardNum?: number,
    shardNodeCount?: number,
    isApply?: boolean
    originSpecId?: number | string
  }

  interface Emits {
    (e: 'currentChange', value?: RedisClusterSpecRow): void
  }

  const props = withDefaults(defineProps<Props>(), {
    shardNum: 0,
    shardNodeCount: 0,
    isApply: true,
    originSpecId: undefined,
  });
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<{
    spec_id: number | string,
    capacity: number | string,
  }>({
    required: true,
  });

  const { t } = useI18n();

  const specRef = ref();
  const specList = ref<RedisClusterSpecRow[]>([]);

  let timer = 0;

  const columns = computed(() => [
    {
      field: 'spec_name',
      showOverflowTooltip: false,
      renderHead: () => (
        <bk-popover
          theme="light"
          extCls='mongo-config-spec-name-popover'>
          {{
            default: () => <span class='spec-name-head'>{t('资源规格')}</span>,
            content: () => <img src={SpecTip} width={200}></img>,
          }}
        </bk-popover>
      ),
      render: ({ data, index }: { data: RedisClusterSpecRow, index: number }) => {
        let tag;
        if (props.originSpecId === data.spec_id) {
          tag = (
            <MiniTag
              class='ml-2'
              theme="info"
              content={t('当前方案')} />
          );
        } else if (data.machine_num > data.count) {
          tag = (
            <MiniTag
              class='ml-2'
              theme="danger"
              content={t('资源不足')} />
          );
        }

        return (
          <div class="spec-id-box">
            <bk-radio
              v-model={modelValue.value.spec_id}
              label={data.spec_id}
              key={index}
              class="spec-radio"
              onClick={(event: Event) => handleRowClick(event, data)}>
              <div
                class="text-overflow"
                v-overflow-tips
                onClick={(event: Event) => event.stopPropagation()}>
                {data.spec_name}
              </div>
            </bk-radio>
            { tag }
          </div>
        );
      },
    },
    {
      field: 'shard_node_num',
      label: t('每个Shard节点数'),
      width: 130,
    },
    {
      field: 'shard_num',
      label: t('Shard数量'),
      width: 100,
      render: ({ data, index }: { data: RedisClusterSpecRow, index: number }) => {
        if (props.isApply) {
          return (
            <bk-select
              modelValue={data.shard_num}
              clearable={false}
              class='shard-node-spec'
              onChange={(value: string) => handleShardNumChange(value, index, 'shard_num')}>
              {
                data.shard_choices.map((item, index) => (
                  <bk-option
                    key={index}
                    label={item.shard_num}
                    value={item.shard_num}>
                  </bk-option>
                ))
              }
            </bk-select>
          );
        }

        return <span>{ data.shard_num }</span>;
      },
    },
    {
      field: 'shard_node_spec',
      label: t('Shard节点规格'),
      render: ({ data }: { data: RedisClusterSpecRow }) => {
        // if (props.isApply) {
        const index = data.shard_choices.findIndex(choiceItem => choiceItem.shard_num === data.shard_num);
        return <span>{ index > -1 ? data.shard_choices[index].shard_spec : '--' }</span>;
        // }

        // return (
        //   <bk-popover
        //     content={t('暂无其他分片规格可切换')}
        //     disabled={data.shard_choices.length > 0}>
        //     <bk-select
        //       modelValue={data.shard_num}
        //       clearable={false}
        //       filterable={true}
        //       disabled={data.shard_choices.length === 0}
        //       class='shard-node-spec'>
        //       {
        //         data.shard_choices.map((item, index) => (
        //           <bk-option
        //             key={index}
        //             label={item.shard_spec}
        //             value={item.shard_num}>
        //           </bk-option>
        //         ))
        //       }
        //     </bk-select>
        //   </bk-popover>
        // );
      },
    },
    {
      field: 'machine_pair',
      label: t('所需机组数'),
      width: 96,
    },
    {
      field: 'machine_num',
      label: t('所需机器数'),
      width: 96,
    },
    {
      field: 'count',
      label: t('可用主机数'),
      width: 96,
    },
  ]);

  const {
    run: getFilterClusterSpecRun,
    loading: isLoading,
  } = useRequest(getFilterClusterSpec, {
    manual: true,
    onSuccess(res) {
      const shardNodeNum = props.isApply ? 3 : props.shardNodeCount; // 节点数，部署时固定，容量变更取自集群信息
      specList.value = res.map(item => Object.assign(item, {
        shard_node_num: shardNodeNum,
        shard_num: props.isApply ? item.shard_recommend.shard_num : props.shardNum,
        shard_node_spec: '',
        machine_num: item.machine_pair * shardNodeNum, // 机器组数 x 每个Shard节点数
        count: 0,
      } as RedisClusterSpecRow));
      getSpecResourceCountRun({
        bk_biz_id: Number(props.bizId),
        bk_cloud_id: Number(props.cloudId),
        spec_ids: specList.value.map(item => item.spec_id),
      });
    },
    onError() {
      specList.value = [];
    },
  });

  const { run: getSpecResourceCountRun } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value = specList.value.map(item => Object.assign(item, {
        count: data[item.spec_id] ?? 0,
      }));
    },
  });

  watch(() => modelValue.value.spec_id, (newSpecId) => {
    if (newSpecId) {
      specRef.value.clearValidate();
    } else {
      emits('currentChange');
    }
  });

  watch(() => modelValue.value.capacity, (newCapacity) => {
    if (!props.isApply) {
      modelValue.value.spec_id = props.originSpecId as number | string;
    }

    if (newCapacity === '') {
      specList.value = [];
    } else {
      clearTimeout(timer);
      timer = setTimeout(() => {
        fetchFilterClusterSpec();
      }, 400);
    }
  });

  const handleCapacityChange = (value: number) => {
    modelValue.value.capacity = value;
  };

  const handleShardNumChange = (value: string, index: number, fieldName: string) => {
    const specListCopy = _.cloneDeep(specList.value);
    const specItem = specListCopy[index];
    Object.assign(specItem, { [fieldName]: value });

    specList.value = specListCopy;
    emits('currentChange', specItem);
  };

  const fetchFilterClusterSpec = () => {
    const { capacity } = modelValue.value;

    if (!capacity) {
      return;
    }

    getFilterClusterSpecRun({
      spec_cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
      spec_machine_type: MachineTypes.MONGODB,
      capacity: Number(modelValue.value.capacity),
      shard_num: props.shardNum,
    });
  };
  fetchFilterClusterSpec();

  const handleRowClick = (event: Event, row: RedisClusterSpecRow) => {
    modelValue.value.spec_id = row.spec_id;
    emits('currentChange', row);
  };
</script>

<style lang="less" scoped>
  .mongo-config-spec {
    max-width: 1200px;
    border-radius: 2px;

    .capacity-label {
      :deep(.bk-form-label) {
        font-weight: 700;
      }
    }

    :deep(.spec-name-head) {
      text-decoration-style: dashed;
      text-decoration-line: underline;
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    :deep(.spec-id-box) {
      display: flex;
      align-items: center;
    }

    :deep(.spec-radio) {
      max-width: 100%;
      overflow: hidden;

      .bk-radio-input {
        flex-shrink: 0;
      }

      .bk-radio-label {
        flex: 1;
        overflow: hidden;
      }
    }

    .custom-edit-table {
      :deep(.bk-table-body) {
        .cell {
          height: 42px !important;
        }

        tr:hover td {
          background-color: #f5f7fa !important;
        }
      }
    }
  }

  .mongo-config-spec-apply {
    padding: 24px 24px 24px 0;
    background-color: #f5f7fa;
  }
</style>

<style>
  .mongo-config-spec-name-popover {
    padding: 16px !important;
  }
</style>
