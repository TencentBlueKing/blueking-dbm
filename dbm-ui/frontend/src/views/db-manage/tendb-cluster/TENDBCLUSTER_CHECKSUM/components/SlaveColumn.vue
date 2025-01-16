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
    :disabled-method="disabledMethod"
    field="slave"
    :label="t('校验从库')"
    :min-width="200">
    <Block v-if="rowData.scope === 'all'">
      {{ t('全部') }}
    </Block>
    <div
      v-else
      class="render-instance"
      @click="handleShowSelector">
      <Block v-if="modelValue.length > 0">
        <div
          v-for="item in modelValue"
          :key="item"
          class="instance-item">
          {{ item }}
        </div>
      </Block>
      <Block
        v-else
        :placeholder="t('请选择')" />
    </div>
  </Column>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import { Block, Column } from '@components/editable-table/Index.vue';
  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    rowData: {
      cluster: {
        id: number;
      };
      scope: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: [
      {
        name: t('主库故障主机'),
        topoConfig: {
          filterClusterId: props.rowData.cluster.id,
        },
        tableConfig: {
          firsrColumn: {
            label: 'slave',
            field: 'instance_address',
            role: 'remote_slave',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const showSelector = ref(false);

  watch(
    () => props.rowData.scope,
    () => {
      modelValue.value = [];
    },
  );

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (payload: InstanceSelectorValues<IValue>) => {
    modelValue.value = payload.tendbcluster.map((item) => item.instance_address);
  };

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'slave' && !rowData.scope) {
      return t('请先选择集群及校验范围');
    }
    return '';
  };
</script>
<style lang="less" scoped>
  .render-instance {
    flex: 1;
    cursor: pointer;

    .instance-item {
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
