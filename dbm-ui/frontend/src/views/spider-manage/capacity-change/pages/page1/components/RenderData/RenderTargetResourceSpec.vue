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
  <span
    v-bk-tooltips="{
      disabled: Boolean(clusterData),
      content: t('请先选择集群')
    }">
    <TableEditInput
      ref="inputRef"
      :disabled="!clusterData"
      :model-value="`${localSpec ? localSpec.capacity + ' G' : ''}`"
      :placeholder="t('请选择')"
      readonly
      :rules="rules"
      @click="handleShowSelector" />
  </span>
  <DbSideslider
    v-model:is-show="isShowSelector"
    :width="960">
    <div
      v-if="clusterData"
      class="cluster-spec-plan-selector-box">
      <div class="spec-box mb-24">
        <table>
          <tr>
            <td>{{ t('当前规格') }}:</td>
            <td>{{ clusterData.cluster_spec.spec_name }}</td>
            <td>{{ t('变更后规格') }}:</td>
            <td>{{ futureSpec.name }}</td>
          </tr>
          <tr>
            <td>{{ t('当前容量') }}:</td>
            <td>{{ clusterData.cluster_capacity }} G</td>
            <td>{{ t('变更后容量') }}:</td>
            <td>{{ futureSpec.futureCapacity }} G</td>
          </tr>
        </table>
      </div>
      <BkForm form-type="vertical">
        <ClusterSpecPlanSelector
          :cloud-id="clusterData.bk_cloud_id"
          cluster-type="tendbcluster"
          machine-type="remote"
          @change="handlePlanChange" />
      </BkForm>
    </div>
  </DbSideslider>
</template>
<script lang="ts">
  export default {
    inheritAttrs: false,
  };
</script>
<script setup lang="ts">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type SpiderModel from '@services/model/spider/spider';

  import ClusterSpecPlanSelector, {
    type IRowData,
  } from '@components/cluster-spec-plan-selector/Index.vue';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  interface Props {
    clusterData?: SpiderModel
  }
  interface Exposes {
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const inputRef = ref();
  const isShowSelector = ref(false);
  const futureSpec = ref({
    name: '',
    futureCapacity: 0,
  });
  const localSpec = shallowRef<IRowData>();

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标总容量不能为空'),
    },
  ];

  watch(() => props.clusterData, () => {
    if (!props.clusterData) {
      futureSpec.value = {
        name: '',
        futureCapacity: 0,
      };
      localSpec.value = undefined;
    }
  });

  const handleShowSelector = () => {
    if (!props.clusterData) {
      return;
    }
    isShowSelector.value = true;
  };

  const handlePlanChange = (specId: number, specData: IRowData) => {
    localSpec.value = specData;
  };

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          resource_spec: {
            backend_group: {
              spec_id: localSpec.value?.spec_id,
              count: localSpec.value?.machine_pair,
              affinity: '',
            },
          },
        }));
    },
  });
</script>
<style lang="less">
  .cluster-spec-plan-selector-box{
    padding: 20px 40px;

    .spec-box{
      width: 100%;
      padding: 16px 0;
      font-size: 12px;
      line-height: 18px;
      background-color: #FAFBFD;

      table{
        width: 100%;
        table-layout: fixed;
      }

      td{
        height: 18px;
        padding-left: 16px;

        &:nth-child(2n+1){
          text-align: right;
        }
      }
    }
  }
</style>
