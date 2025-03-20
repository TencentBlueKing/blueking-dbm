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
  <div class="monitor-targets-box">
    <DimensionItem
      v-for="(item, index) in dimensionList"
      :key="item.key"
      ref="dimensionItemRefs"
      :data="item"
      :db-type="dbType"
      :disabled="disabled"
      :excludes="excludes"
      :is-fixed="index === 0"
      :is-single="dimensionList.length === 1"
      :show-add="dimensionList.length < typeList.length"
      :show-delete="index > 0"
      :show-link="index < dimensionList.length - 1"
      @add="() => handleAddItem(index)"
      @delete="() => handleDeleteItem(index)"
      @type-change="handleTypeChange" />
  </div>
</template>
<script setup lang="ts">
  import AlarmShieldModel from '@services/model/monitor/alarm-shield';

  import { random } from '@utils';

  import DimensionItem from './components/DimensionItem.vue';

  export interface Exposes {
    getValue: () => {
      dimension_conditions: {
        condition: string;
        key: string;
        method: string;
        name: string;
        value: (number | string)[];
      }[];
    };
  }

  interface Props {
    data?: AlarmShieldModel['dimension_config'];
    dbType?: string;
    disabled?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    dbType: '',
    disabled: false,
  });

  const createEmptyItem = () => ({
    condition: '',
    key: random(),
    method: '',
    name: '',
    value: [] as string[],
  });

  const dimensionList = ref([createEmptyItem()]);
  const excludes = ref<string[]>(['biz']);
  const dimensionItemRefs = ref<InstanceType<typeof DimensionItem>[]>([]);

  const typeList = ['appid', 'cluster_domain', 'instance_role', 'instance', 'instance_host'];

  watchEffect(() => {
    if (props.data) {
      if (props.data.dimension_conditions) {
        dimensionList.value = props.data.dimension_conditions;
        return;
      }

      if (props.data.bk_target_ip) {
        dimensionList.value = [
          {
            condition: 'and',
            key: 'instance_host',
            method: 'eq',
            name: 'instance_host',
            value: props.data.bk_target_ip.map((item) => item.bk_target_ip),
          },
        ];
        return;
      }
    }
    dimensionList.value = [createEmptyItem()];
  });

  const handleAddItem = (index: number) => {
    dimensionList.value.splice(index + 1, 0, createEmptyItem());
    nextTick(() => {
      handleTypeChange();
    });
  };

  const handleDeleteItem = (index: number) => {
    const type = dimensionItemRefs.value[index].getValue().key;
    const typeIndex = excludes.value.indexOf(type);
    excludes.value.splice(typeIndex, 1);
    nextTick(() => {
      dimensionList.value.splice(index, 1);
    });
  };

  const handleTypeChange = () => {
    excludes.value = dimensionItemRefs.value.reduce<string[]>((results, item) => {
      if (item.getValue().key) {
        results.push(item.getValue().key);
      }
      return results;
    }, []);
  };

  defineExpose<Exposes>({
    getValue() {
      const infos = dimensionItemRefs.value.map((item) => item.getValue());
      return {
        dimension_conditions: infos.map((info) => ({
          condition: 'and',
          key: info.key,
          method: info.method,
          name: info.key,
          value: info.values,
        })),
      };
    },
  });
</script>
<style lang="less" scoped>
  .monitor-targets-box {
    width: 100%;
    user-select: none;
  }
</style>
