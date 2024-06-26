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
  <div class="render-host-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="t('请输入或选择')"
      :rules="rules"
      @submit="handleInputFinish" />
  </div>
</template>

<script lang="ts">
  const hostsMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  interface Props {
    ip?: string;
  }

  interface Emits {
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    ip: '',
  });
  const emits = defineEmits<Emits>();

  const instanceKey = `render_host_${random()}`;
  hostsMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const localValue = ref(props.ip);
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('IP不能为空'),
    },
    {
      validator: (value: string) => ipv4.test(value),
      message: t('IP格式不正确'),
    },
    {
      validator: async (value: string) => {
        const data = await checkMysqlInstances({
          bizId: currentBizId,
          instance_addresses: [value],
        });
        if (data.length > 0) {
          localValue.value = data[0].ip;
          return true;
        }
        return false;
      },
      message: t('目标主机不存在'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = hostsMemo[instanceKey];
        const otherClusterMemoMap = { ...hostsMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce(
          (result, item) => ({
            ...result,
            ...item,
          }),
          {} as Record<string, boolean>,
        );

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('目标主机重复'),
    },
  ];

  // 同步外部值
  watch(
    () => props.ip,
    (newIp) => {
      if (newIp) {
        localValue.value = newIp;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    localValue,
    () => {
      if (localValue.value) {
        hostsMemo[instanceKey][localValue.value] = true;
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    hostsMemo[instanceKey][localValue.value] = true;
    emits('inputFinish', value);
  };

  onBeforeUnmount(() => {
    delete hostsMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => localValue.value)
        .catch(() => Promise.reject(localValue.value));
    },
  });
</script>

<style lang="less" scoped>
  .render-host-box {
    position: relative;
  }
</style>
