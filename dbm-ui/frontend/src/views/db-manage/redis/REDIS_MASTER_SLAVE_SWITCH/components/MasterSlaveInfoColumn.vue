<template>
  <EditableColumn
    :label="t('待切换的 Master 实例')"
    :loading="loading"
    :width="200">
    <EditableBlock :placeholder="t('输入主机后自动生成')">
      <div
        v-for="(masterInstanceItem, masterInstanceIndex) in modelValue?.master_instances"
        :key="masterInstanceIndex">
        {{ masterInstanceItem }}
      </div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :label="t('待切换的从库主机')"
    :loading="loading"
    :width="200">
    <EditableBlock :placeholder="t('输入主机后自动生成')">
      {{ modelValue?.slave_ip }}
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryMachineInstancePair } from '@services/source/redisToolbox';

  const modelValue = defineModel<{
    bk_cloud_id: number;
    ip: string;
    master_instances: string[];
    slave_ip: string;
  }>();

  const { t } = useI18n();

  const { loading, run: runQueryMachineInstancePair } = useRequest(queryMachineInstancePair, {
    manual: true,
    onSuccess(pairResult) {
      const { bk_cloud_id: bkCloudId, ip } = modelValue.value!;
      const machine = `${bkCloudId}:${ip}`;
      const masterIpMap = pairResult.machines!;

      modelValue.value!.master_instances = masterIpMap[machine].related_pair_instances.map((item) => item.instance);
      modelValue.value!.slave_ip = masterIpMap[machine].ip;
    },
  });

  watch(
    () => [modelValue.value?.bk_cloud_id, modelValue.value?.ip],
    () => {
      if (modelValue.value) {
        const { bk_cloud_id: bkCloudId, ip } = modelValue.value;
        if (bkCloudId !== undefined && ip) {
          runQueryMachineInstancePair({ machines: [`${bkCloudId}:${ip}`] });
        }
      }
    },
    {
      immediate: true,
    },
  );
</script>
