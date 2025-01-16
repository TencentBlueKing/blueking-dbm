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
    field="master"
    :label="t('校验主库')"
    :loading="loading"
    :min-width="200">
    <Block v-if="rowData.scope === 'all'">
      {{ t('全部') }}
    </Block>
    <div
      v-else
      class="render-instance">
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
        :placeholder="t('自动生成')" />
    </div>
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';

  import { Block, Column } from '@components/editable-table/Index.vue';

  interface Props {
    rowData: {
      cluster: {
        id: number;
      };
      scope: string;
      slave: string[];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const { loading, run: fetchRemoteMachineInstancePair } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess(data) {
      modelValue.value = props.rowData.slave.map((item) => data.instances[item].instance);
    },
  });

  watch(
    () => props.rowData.scope,
    () => {
      modelValue.value = [];
    },
  );

  watch(
    () => props.rowData.slave,
    () => {
      if (props.rowData.slave) {
        fetchRemoteMachineInstancePair({
          instances: props.rowData.slave,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .render-instance {
    flex: 1;

    .instance-item {
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
