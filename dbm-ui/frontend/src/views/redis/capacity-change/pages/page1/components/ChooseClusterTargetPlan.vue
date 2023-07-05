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
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ $t('选择集群目标方案') }}
        【{{ clusterName }}】
        <BkTag theme="info">
          存储层
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="capacity-panel">
        <div class="panel-row">
          <div class="column">
            <div class="title">
              当资源规格：
            </div>
            <div class="content">
              4核16GB_500GB_QPS:1000
            </div>
          </div>
          <div class="column">
            <div class="title">
              变更后的规格：
            </div>
            <div class="content">
              4核16GB_500GB_QPS:1000
            </div>
          </div>
        </div>
        <div
          class="panel-row"
          style="margin-top: 12px;">
          <div class="column">
            <div class="title">
              当前容量：
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
              <span class="percent">93.12%</span>
              <span class="spec">(412G/500G)</span>
            </div>
          </div>
          <div class="column">
            <div class="title">
              变更后容量：
            </div>
            <div class="content">
              <BkProgress
                color="#2DCB56"
                :percent="50"
                :show-text="false"
                size="small"
                :stroke-width="16"
                type="circle"
                :width="15" />
              <span class="percent">50%</span>
              <span class="spec">(412G/500G)</span>
              <span class="scale-percent">(+12.00%, +500G)</span>
            </div>
          </div>
        </div>
      </div>
      <div class="select-group">
        <div class="select-box">
          <div class="title-spot">
            目标集群容量需求<span class="edit-required" />
          </div>
          <div class="input-box">
            <BkInput
              v-model="capacityNeed"
              class="mb10"
              clearable
              :max="100"
              :min="1"
              size="small"
              type="number" />
            <div class="uint">
              G
            </div>
          </div>
        </div>
        <div class="select-box">
          <div class="title-spot">
            未来集群容量需求<span class="edit-required" />
          </div>
          <div class="input-box">
            <BkInput
              v-model="capacityFutureNeed"
              class="mb10"
              clearable
              :max="100"
              :min="1"
              size="small"
              type="number" />
            <div class="uint">
              G
            </div>
          </div>
        </div>
      </div>
      <div class="qps-box">
        <div class="title-spot">
          QPS 预估范围<span class="edit-required" />
        </div>
        <BkSlider
          v-model="qpsRange"
          :formatter-label="formatterLabel"
          :max-value="5000"
          :min-value="0"
          range
          show-interval
          show-interval-label
          :step="1000" />
      </div>
      <div class="deploy-box">
        <div class="title-spot">
          集群部署方案<span class="edit-required" />
        </div>
        <DbOriginalTable
          class="deploy-table"
          :columns="columns"
          :data="tableData" />
      </div>
    </div>

    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleConfirm">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/ticket';
  import type { ResourceRedisItem } from '@services/types/clusters';

  import { useBeforeClose, useStickyFooter, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import { generateId } from '@utils';

  import specTipImg from '@images/spec-tip.png';


  interface Props {
    isShow?: boolean;
    clusterName?: string;
  }

  interface Emits {
    (e: 'update:is-show', value: boolean): void,
    (e: 'on-confirm', value: string): void
  }

  interface DataItem {
    spec: string,
    tip_type: string,
    machine_num: number,
    cluster_slice: number,
    cluster_capacity: number,
    cluster_qps: number,
    unchecked: boolean,
  }

  withDefaults(defineProps<Props>(), {
    isShow: false,
    clusterName: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const capacityNeed = ref(0);
  const capacityFutureNeed = ref(0);
  const radioValue  = ref('');
  const qpsRange = ref([0, 1000]);

  const globalBizsStore = useGlobalBizs();
  const handleBeforeClose = useBeforeClose();

  const formatterLabel = (value: string) => <span>{value}/s</span>;

  const tableData = ref([
    {
      spec: '4核16G_500G_100/s',
      tip_type: '推荐',
      machine_num: 1,
      cluster_slice: 2,
      cluster_capacity: 100,
      cluster_qps: 1000,
    },
    {
      spec: '4核16G_200G_100/s',
      tip_type: '当前方案',
      machine_num: 1,
      cluster_slice: 2,
      cluster_capacity: 100,
      cluster_qps: 1000,
    },
    {
      spec: '4核16G_300G_10000/s',
      tip_type: '资源不足',
      machine_num: 1,
      cluster_slice: 2,
      cluster_capacity: 100,
      cluster_qps: 1000,
    },
  ]);

  const columns = [
    {
      label: () => <bk-popover
        theme="light"
        class="tip-box"
        width="210"
        height="78"
        >
          {{
            default: () => <div style="border-bottom: 1px dashed #979BA5;">{t('资源规格')}</div>,
            content: () => <img style="width:182px;height:63px" src={specTipImg} />,
          }}
        </bk-popover>,
      field: 'spec',
      showOverflowTooltip: false,
      width: 260,
      render: ({ data }: { data: DataItem }) => (
      <div style="display:flex;align-items:center;">
        <bk-radio label={data.spec} v-model={radioValue.value}/>
        <bk-tag theme={data.tip_type === '推荐' ? 'success' : data.tip_type === '当前方案' ? 'info' : 'danger'} style="margin-left:5px">
          {data.tip_type}
        </bk-tag></div>
    ),
    }, {
      label: t('需机器组数'),
      field: 'machine_num',
      sort: true,
    },
    {
      label: t('集群分片'),
      field: 'cluster_slice',
      sort: true,
    },
    {
      label: t('集群容量(G)'),
      field: 'cluster_capacity',
      sort: true,
    },
    {
      label: t('集群QPS(每秒)'),
      field: 'cluster_qps',
      sort: true,
      render: ({ data }: { data: DataItem }) => <div>{data.cluster_qps}/s</div>,
    }];

  const state = reactive({
    isLoading: false,
    formdata: [] as DataItem[],
    renderKey: generateId('BACKUP_FORM_'),
  });

  // 点击确定
  const handleConfirm = () => {
    // console.log(radioValue.value);
    emits('on-confirm', radioValue.value);
    emits('update:is-show', false);
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    emits('update:is-show', false);
    window.changeConfirm = false;
  }
</script>

<style lang="less" scoped>
.title-spot {
  position: relative;
  width: 100%;
  height: 20px;
  font-family: MicrosoftYaHei-Bold;
  font-size: 12px;
  font-weight: 700;
  color: #63656E;

  .edit-required {
    position: relative;

    &::after {
      position: absolute;
      top: -10px;
      margin-left: 4px;
      font-size: 12px;
      line-height: 40px;
      color: #ea3636;
      content: "*";
    }
  }
}


.main-box {
  display: flex;
  width: 100%;
  padding: 24px 40px;
  flex-direction: column;

  .capacity-panel {
    width: 880px;
    height: 78px;
    padding: 16px;
    margin-bottom: 24px;
    background: #FAFBFD;

    .panel-row {
      display: flex;
      width: 100%;

      .column {
        display: flex;
        width: 50%;

        .title {
          width: 84px;
          height: 18px;
          font-family: MicrosoftYaHei;
          font-size: 12px;
          line-height: 18px;
          letter-spacing: 0;
          color: #63656E;
          text-align: right;
        }

        .content {
          flex:1;
          display: flex;
          font-family: MicrosoftYaHei;
          font-size: 12px;
          color: #63656E;

          .percent {
            margin-left: 4px;
            font-family: Arial-BoldMT;
            font-size: 12px;
            font-weight: bold;
            color: #313238;
          }

          .spec {
            margin-left: 2px;
            font-family: ArialMT;
            font-size: 12px;
            color: #979BA5;
          }

          .scale-percent {
            margin-left: 5px;
            font-family: Arial-BoldMT;
            font-size: 12px;
            font-weight: bold;
            color: #EA3636;
          }
        }
      }
    }
  }

  .select-group {
    display: flex;
    width: 880px;
    margin-bottom: 24px;
    gap: 38px;

    .select-box {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;

      .input-box {
        display: flex;
        width: 100%;
        align-items: center;

        .uint {
          margin-left: 12px;
          font-size: 12px;
          color: #63656E;
        }
      }
    }
  }

  .qps-box {
    display: flex;
    width: 100%;
    margin-bottom: 32px;
    flex-direction: column;
    gap: 10px;
  }

  .deploy-box {
    margin-top: 34px;

    .deploy-table {
      margin-top: 6px;

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

  .spec-title {
    border-bottom: 1px dashed #979BA5;
  }

}


</style>
