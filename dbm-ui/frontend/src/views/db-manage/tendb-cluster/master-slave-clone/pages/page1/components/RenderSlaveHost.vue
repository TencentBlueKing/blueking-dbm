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
  <BkLoading :loading="isLoading">
    <RenderText
      ref="textRef"
      :data="slaveInfo?.ip"
      :placeholder="t('选择目标主库后自动生成')"
      readonly
      :rules="rules" />
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RemotePairInstanceModel from '@services/model/mysql/remote-pair-instance';
  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    cloudId?: number;
    ip?: string;
  }

  interface Emits {
    (e: 'change', value: string): void;
  }

  interface Expose {
    getValue: () => Promise<{
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
      bk_biz_id: number;
    }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('不能为空'),
    },
  ];

  const textRef = ref();
  const slaveInfo = ref<RemotePairInstanceModel>();

  const { loading: isLoading, run: fetchRemoteMachineInstancePair } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess(data) {
      const [machineInstancePair] = Object.values(data.machines);
      slaveInfo.value = machineInstancePair;
      emits('change', machineInstancePair.ip);
      setTimeout(() => {
        // 行复制后，查询到对应数据后消除验证失败的样式
        textRef.value.getValue();
      });
    },
  });

  watch(
    () => props.ip,
    () => {
      if (props.ip) {
        fetchRemoteMachineInstancePair({
          machines: [`${props.cloudId}:${props.ip}`],
        });
      } else {
        slaveInfo.value = undefined;
        emits('change', '');
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Expose>({
    getValue() {
      const slave = slaveInfo.value;
      if (slave) {
        return Promise.resolve({
          ip: slave.ip,
          bk_cloud_id: slave.bk_cloud_id,
          bk_host_id: slave.bk_host_id,
          bk_biz_id: slave.bk_biz_id,
        });
      }
      return textRef.value!.getValue();
    },
  });
</script>
