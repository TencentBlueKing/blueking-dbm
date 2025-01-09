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
  <Column
    field="targetCapacity"
    :label="t('目标总容量')"
    :min-width="150">
    <Input
      v-model="renderText"
      @click="handleShowSelector">
      <template #append>
        <DbIcon type="down-big" />
      </template>
    </Input>
  </Column>
  <DbSideslider
    :before-close="handleClose"
    :is-show="isShowSelector"
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ t('选择集群目标方案_n', { n: cluster.master_domain }) }}
        <BkTag theme="info">
          {{ t('存储层 RemoteDB/DR 同时变更') }}
        </BkTag>
      </span>
    </template>
    <div
      v-if="cluster"
      class="cluster-spec-plan-selector-box">
      <div class="spec-box mb-24">
        <table>
          <tr>
            <td>{{ t('当前规格') }}： {{ cluster.cluster_spec.spec_name }}</td>
            <td>{{ t('变更后规格') }}： {{ futureSpec.spec_name || '--' }}</td>
          </tr>
          <tr>
            <td>{{ t('当前机器组数') }}： {{ cluster.machine_pair_cnt }}</td>
            <td>{{ t('变更机器组数') }}： {{ futureSpec.machine_pair || '--' }}</td>
          </tr>
          <tr>
            <td>
              {{ t('当前容量') }}： <span class="text-bold">{{ cluster.cluster_capacity }} G</span>
            </td>
            <td>
              {{ t('变更后容量') }}： <span class="text-bold">{{ futureSpec.cluster_capacity }} G</span>
            </td>
          </tr>
        </table>
      </div>
      <BkForm label-width="135">
        <ClusterSpecPlanSelector
          v-model:custom-spec-info="customSpecInfo"
          :cloud-id="cluster.bk_cloud_id"
          :cluster-shard-num="cluster.cluster_shard_num"
          cluster-type="tendbcluster"
          machine-type="backend"
          @change="handlePlanChange" />
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useBeforeClose } from '@hooks';

  import { Column, Input } from '@components/editable-table/Index.vue';

  import ClusterSpecPlanSelector, {
    type TicketSpecInfo,
  } from '@views/db-manage/common/cluster-spec-plan-selector/Index.vue';

  interface Props {
    cluster: Pick<
      TendbClusterModel,
      | 'id'
      | 'master_domain'
      | 'bk_cloud_id'
      | 'cluster_capacity'
      | 'cluster_shard_num'
      | 'cluster_spec'
      | 'db_module_id'
      | 'machine_pair_cnt'
      | 'remote_shard_num'
      | 'disaster_tolerance_level'
    >;
  }

  defineProps<Props>();

  const modelValue = defineModel<TicketSpecInfo>({
    default: () => ({
      spec_id: 0,
      spec_name: '',
      machine_pair: 0,
      cluster_capacity: 0,
    }),
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const isShowSelector = ref(false);
  const customSpecInfo = reactive({
    specId: '',
    count: 1,
  });
  const choosedSpecId = ref(-1);
  const futureSpec = reactive<TicketSpecInfo>({
    spec_id: 0,
    spec_name: '',
    machine_pair: 0,
    cluster_capacity: 0,
  });

  const renderText = computed(() => `${choosedSpecId.value !== -1 ? `${modelValue.value.cluster_capacity} G` : ''}`);

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleConfirm = () => {
    modelValue.value = futureSpec;
    isShowSelector.value = false;
  };

  async function handleClose() {
    const result = await handleBeforeClose(choosedSpecId.value !== -1);
    if (!result) {
      return;
    }
    isShowSelector.value = false;
  }

  const handlePlanChange = (specId: number, specData: TicketSpecInfo) => {
    choosedSpecId.value = specId;
    Object.assign(futureSpec, specData);
  };
</script>
<style lang="less" scoped>
  .cluster-spec-plan-selector-box {
    padding: 20px 40px;

    .spec-box {
      width: 100%;
      padding: 16px;
      font-size: 12px;
      line-height: 18px;
      background-color: #fafbfd;

      table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 8px 0;
        table-layout: fixed;
      }

      td {
        height: 18px;

        .text-bold {
          font-weight: bold;
        }
      }
    }
  }
</style>
