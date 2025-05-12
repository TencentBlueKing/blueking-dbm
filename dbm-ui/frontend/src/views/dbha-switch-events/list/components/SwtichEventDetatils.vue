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
  <div class="switch-event-details">
    <DbLog
      ref="logRef"
      :loading="contentLoading" />
  </div>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getEventSwitchLog } from '@services/source/dbha';

  import DbLog from '@components/db-log/index.vue';

  interface Props {
    isActive: boolean;
    uid: number;
  }

  const props = defineProps<Props>();

  const logRef = ref<InstanceType<typeof DbLog>>();

  const { loading: contentLoading, run: fetchEventSwitchLog } = useRequest(getEventSwitchLog, {
    manual: true,
    onSuccess(data) {
      logRef.value?.setLog(data);
    },
  });

  watch(
    () => props.isActive,
    () => {
      if (props.isActive) {
        if (props.uid) {
          fetchEventSwitchLog({ sw_id: props.uid });
        }
        setTimeout(() => {
          logRef.value?.init();
        });
      } else {
        logRef.value!.destroy();
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .switch-event-details {
    height: calc(100vh - var(--notice-height) - 90px);
    padding: 16px 16px 0;
  }
</style>
