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
  <DbSideslider
    :before-close="handleClose"
    :is-show="isShowSelector"
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ t('选择集群目标方案_n', { n: data.clusterName }) }}
        <BkTag theme="info">
          {{ t('存储层') }}
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="capacity-panel">
        <div class="panel-row">
          <div class="column">
            <div class="title">{{ t('当前资源规格') }}：</div>
            <div class="content">
              {{ data.currentSepc }}
            </div>
          </div>
          <div class="column">
            <div class="title">{{ t('变更后的规格') }}：</div>
            <div class="content">
              <span v-if="targetSepc">{{ targetSepc }}</span>
              <span
                v-else
                style="color: #c4c6cc">{{ t('请先选择部署方案') }}</span>
            </div>
          </div>
        </div>
        <!-- <div
          class="panel-row"
          style="margin-top: 12px;">
          <div class="column">
            <div
              class="title"
              style="min-width: 70px;">
              {{ t('当前总容量') }}：
            </div>
            <div class="content">
              <BkProgress
                color="#EA3636"
                :percent="35"
                :show-text="false"
                size="small"
                :stroke-width="16"
                type="circle"
                :width="15" />
              <span class="percent">{{ currentPercent }}%</span>
              <span class="spec">{{ `(${data.currentCapacity.used}G/${targetCapacity.total}G)` }}</span>
            </div>
          </div>
          <div class="column">
            <div
              class="title"
              style="min-width: 82px;">
              {{ t('变更后总容量') }}：
            </div>
            <div class="content">
              <template v-if="targetSepc">
                <BkProgress
                  color="#2DCB56"
                  :percent="targetPercent"
                  :show-text="false"
                  size="small"
                  :stroke-width="16"
                  type="circle"
                  :width="15" />
                <span class="percent">{{ targetPercent }}%</span>
                <span class="spec">{{ `(${data.currentCapacity.used}G/${targetCapacity.total}G)` }}</span>
                <span
                  class="scale-percent"
                  :style="{color: targetCapacity.total > targetCapacity.current ? '#ea3636' : '#2dcb56'}"
                  {{ `(${changeObj.rate}%, ${changeObj.num}G)` }}
                </span>
                <span
                  class="scale-percent"
                  :style="{color: targetCapacity.total > targetCapacity.current ? '#ea3636' : '#2dcb56'}"
                  {{ `(${changeObj.num}G)` }}
                </span>
              </template>
              <span
                v-else
                style="color: #C4C6CC;">{{ t('请先选择部署方案') }}</span>
            </div>
          </div>
        </div> -->
      </div>
      <div class="select-group">
        <div class="select-box">
          <div class="title-spot">{{ t('目标集群容量需求') }}<span class="required" /></div>
          <div class="input-box">
            <BkInput
              v-model="capacityNeed"
              class="num-input"
              :min="0"
              size="small"
              type="number"
              @blur="handleSearchClusterSpec" />
            <div class="uint">G</div>
          </div>
        </div>
      </div>
      <div class="deploy-box">
        <div class="title-spot">{{ t('集群部署方案') }}<span class="required" /></div>
        <BkLoading :loading="isTableLoading">
          <DbOriginalTable
            class="deploy-table"
            :columns="columns"
            :data="tableData"
            @column-sort="handleColumnSort"
            @row-click.stop="handleRowClick">
            <template #empty>
              <p
                v-if="!capacityNeed || !capacityFutureNeed"
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
        </BkLoading>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!isAbleSubmit"
        :loading="isConfirmLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isConfirmLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import SpecTip from '@images/spec-tip.png';

  import type { IDataRow } from './Row.vue';

  export interface Props {
    data: IDataRow;
  }

  export type ClusterSpec = ServiceReturnType<typeof getFilterClusterSpec>[0] & {
    shard_node_count: number,
    shard_num: number,
    available_machines: number,
    machine_need_num: number,
    id: number,
    name: string,
  };

  interface Emits {
    (e: 'confirm', obj: ClusterSpec): void
    (e: 'cancel'): void
  }


  const props  = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShowSelector = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const { currentBizId } = useGlobalBizs();

  const capacityNeed = ref();
  const capacityFutureNeed = ref();
  const radioValue  = ref(-1);
  const radioChoosedId  = ref(''); // 标记，sort重新定位index用
  const isTableLoading = ref(false);
  const isConfirmLoading = ref(false);
  const tableData = ref<ClusterSpec[]>([]);
  const targetCapacity = ref({
    current: props.data.currentCapacity.total ?? 1,
    total: 1,
  });
  const targetSepc = ref('');

  // const isShowGreaterTip = computed(() => capacityFutureNeed.value < capacityNeed.value);
  const isAbleSubmit = computed(() => radioValue.value !== -1);

  // const currentPercent = computed(() => {
  //   if (props?.data) {
  //     return Number(((props.data.currentCapacity.used / props.data.currentCapacity.total) * 100).toFixed(2));
  //   }
  //   return 0;
  // });

  // const currentSpec = computed(() => {
  //   if (props?.data) {
  //     return `(${props.data.capacity.used}G/${props.data.capacity.total}G)`;
  //   }
  //   return '(0G/0G)';
  // });

  // const currentSpec = computed(() => {
  //   if (props?.data) {
  //     return `${props.data.currentCapacity.total}G`;
  //   }
  //   return '(0G)';
  // });

  // const targetPercent = computed(() => Number(((props.data.currentCapacity.used
  //   / targetCapacity.value.total) * 100).toFixed(2)));

  // const changeObj = computed(() => {
  //   const diff = targetCapacity.value.total - targetCapacity.value.current;
  //   const rate = ((diff / targetCapacity.value.current) * 100).toFixed(2);
  //   if (diff < 0) {
  //     return {
  //       rate,
  //       num: diff,
  //     };
  //   }
  //   return {
  //     rate: `+${rate}`,
  //     num: `+${diff}`,
  //   };
  // });

  // const isDataChange = computed(() => capacityNeed.value !== undefined || capacityFutureNeed.value !== undefined
  //   || radioValue.value !== -1);

  const columns = [
    {
      label: t('资源规格'),
      field: 'spec',
      showOverflowTooltip: true,
      width: 150,
      renderHead: () => (
        <bk-popover theme="light">
          {{
            default: () => <span style="text-decoration-style: dashed;text-decoration-line: underline;">{t('资源规格')}</span>,
            content: () => <img src={SpecTip} width={200}></img>,
          }}
        </bk-popover>
      ),
      render: ({ index, data }: { index: number, data: ClusterSpec }) => (
        <TextOverflowLayout>
          {{
            prepend: () => <bk-radio label={index} v-model={radioValue.value}></bk-radio>,
            default: () => <span style="margin-left:8px;">{data.spec_name}</span>,
            append: () => {
              if (props.data.spec?.id === data.spec_id) {
                return (
                  <bk-tag
                    size="small"
                    class='ml-2'
                    theme="info">
                    { t('当前方案') }
                  </bk-tag>
                );
              } 
              if (data.machine_need_num > data.available_machines) {
                return (
                  <bk-tag
                    size="small"
                    class='ml-2'
                    theme="danger">
                    { t('资源不足') }
                  </bk-tag>
                );
              }
              
              return null
            }
          }}
        </TextOverflowLayout>
      )
    },
    {
      label: t('每个Shard节点数'),
      field: 'shard_node_count',
    },
    {
      label: t('Shard数量'),
      field: '',
      render: ({ data }: { data: ClusterSpec }) => <span>{data.shard_choices[0].shard_num}</span>,
    },
    {
      label: t('Shard节点规格'),
      field: 'cluster_shard_num',
      render: ({ data }: { data: ClusterSpec }) => <span>{data.shard_choices[0].shard_spec}</span>,
    },
    {
      label: t('所需机组数'),
      field: 'machine_pair',
    },
    {
      label: t('所需机器数'),
      field: 'machine_need_num',
      render: ({ data }: { data: ClusterSpec }) => <span>{data.machine_pair * data.shard_node_count}</span>,
    },
    {
      label: t('可用机器数'),
      field: 'available_machines',
    },
  ];

  let rawTableData: ClusterSpec[] = [];

  watch(() => props.data, (data) => {
    if (data) {
      targetCapacity.value.current = data.currentCapacity.total;
    }
  }, {
    immediate: true,
  });

  watch(radioValue, (index) => {
    if (index === -1) return;
    const plan = tableData.value[index];
    targetCapacity.value.total = plan.cluster_capacity;
    targetSepc.value = plan.spec_name;
  });

  const handleSearchClusterSpec = async () => {
    if (capacityNeed.value === undefined) {
      return;
    }
    if (capacityNeed.value > 0) {
      isTableLoading.value = true;
      const params = {
        spec_cluster_type: 'MongoShardedCluster',
        spec_machine_type: 'mongodb',
        capacity: capacityNeed.value,
        shard_num: props.data.shardNum,
      };
      const retArr = await getFilterClusterSpec(params).finally(() => {
        isTableLoading.value = false;
      });
      const ids = retArr.map(item => item.spec_id);
      const specCountMap = await getSpecResourceCount({
        bk_biz_id: currentBizId,
        bk_cloud_id: props.data.bkCloudId,
        spec_ids: ids,
      });
      const list = retArr.map(item => ({
        ...item,
        shard_num: props.data.shardNum,
        shard_node_count: props.data.shardNodeCount,
        machine_need_num: item.machine_pair * props.data.shardNodeCount,
        available_machines: specCountMap[item.spec_id],
        id: item.spec_id,
        name: item.spec_name,
      }));
      tableData.value = list;
      rawTableData = _.cloneDeep(list);
    }
  };

  const handleRowClick = (event: PointerEvent, row: ClusterSpec, index: number) => {
    radioValue.value = index;
    radioChoosedId.value = row.spec_name;
  };

  const handleColumnSort = (data: { column: { field: string }, index: number, type: string }) => {
    const { column, type } = data;
    const filed = column.field as keyof ClusterSpec;
    if (type === 'asc') {
      tableData.value.sort((prevItem, nextItem) => prevItem[filed] as number - (nextItem[filed] as number));
    } else if (type === 'desc') {
      tableData.value.sort((prevItem, nextItem) => nextItem[filed] as number - (prevItem[filed] as number));
    } else {
      tableData.value = rawTableData;
    }
    const index = tableData.value.findIndex(item => item.spec_name === radioChoosedId.value);
    radioValue.value = index;
  };

  // 点击确定
  const handleConfirm = () => {
    const index = radioValue.value;
    if (index === -1) {
      return;
    }
    emits('confirm', tableData.value[index]);
    isShowSelector.value = false;
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    emits('cancel');
    isShowSelector.value = false;
  }
</script>

<style lang="less" scoped>
  .main-box {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

    .capacity-panel {
      width: 880px;
      padding: 16px;
      margin-bottom: 24px;
      background: #fafbfd;

      .panel-row {
        display: flex;
        width: 100%;

        .column {
          display: flex;
          width: 50%;
          align-items: center;

          .title {
            height: 18px;
            font-size: 12px;
            line-height: 18px;
            letter-spacing: 0;
            color: #63656e;
            text-align: right;
          }

          .content {
            flex: 1;
            display: flex;
            font-size: 12px;
            color: #63656e;

            .percent {
              margin-left: 4px;
              font-size: 12px;
              font-weight: bold;
              color: #313238;
            }

            .spec {
              margin-left: 2px;
              font-size: 12px;
              font-weight: bold;
              color: #63656e;
            }

            .scale-percent {
              margin-left: 5px;
              font-size: 12px;
              font-weight: bold;
            }
          }
        }
      }
    }

    .select-group {
      position: relative;
      display: flex;
      width: 880px;
      gap: 38px;

      .select-box {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;

        .input-box {
          display: flex;
          align-items: center;
          width: 400px;

          .num-input {
            height: 32px;
          }

          .uint {
            margin-left: 12px;
            font-size: 12px;
            color: #63656e;
          }
        }

        .gt-tip {
          position: absolute;
          right: 252px;
          bottom: -20px;

          span {
            font-size: 12px;
            color: #ea3636;
          }
        }
      }
    }

    .deploy-box {
      margin-top: 24px;

      .deploy-table {
        margin-top: 6px;

        :deep(.cluster-name) {
          padding: 8px 0;
          line-height: 16px;
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

    .spec-title {
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
