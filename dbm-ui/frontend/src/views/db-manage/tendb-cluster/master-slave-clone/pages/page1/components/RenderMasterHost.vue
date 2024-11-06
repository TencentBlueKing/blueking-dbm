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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    ip?: string;
    inputedIps?: string[];
  }

  interface Emits {
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_id: number;
      old_master: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    ip: '',
    inputedIps: () => [],
  });

  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const localValue = ref(props.ip);
  const editRef = ref();
  const hostInfo = ref<ServiceReturnType<typeof checkMysqlInstances>[number]>();

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
          [hostInfo.value] = data;
          localValue.value = data[0].ip;
          emits('inputFinish', value);
          return true;
        }
        return false;
      },
      message: t('目标主机不存在'),
    },
    {
      validator: (value: string) => props.inputedIps.filter((item) => item === value).length < 2,
      message: t('目标主机重复'),
    },
  ];

  // 同步外部值
  watch(
    () => props.ip,
    () => {
      if (props.ip) {
        localValue.value = props.ip;
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
        setTimeout(() => {
          editRef.value!.getValue();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value!.getValue().then(() => ({
        cluster_id: hostInfo.value?.cluster_id,
        old_master: {
          ip: hostInfo.value?.ip,
          bk_cloud_id: hostInfo.value?.bk_cloud_id,
          bk_host_id: hostInfo.value?.bk_host_id,
          bk_biz_id: currentBizId,
        },
      }));
    },
  });
</script>

<style lang="less" scoped>
  .render-host-box {
    position: relative;
  }
</style>
