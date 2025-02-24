<template>
  <DbFormItem
    class="cluster-authorize-bold"
    :label="t('访问源')"
    property="source_ips"
    required
    :rules="rules">
    <IpSelector
      :biz-id="bizId"
      button-text="添加 IP"
      :data="selected"
      :is-cloud-area-restrictions="false"
      :only-alive-host="false"
      :panel-list="['staticTopo', 'manualInput', 'dbmWhitelist']"
      service-mode="all"
      @change="handleChangeIP"
      @change-whitelist="handleChangeWhitelist" />
  </DbFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getWhitelist } from '@services/source/whitelist';
  import type { HostInfo } from '@services/types';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  export interface SourceIp {
    bk_biz_id?: number;
    bk_host_id?: number;
    ip: string;
  }

  interface Exposes {
    init(data: HostInfo[]): void;
  }

  const sourceIps = defineModel<SourceIp[]>('modelValue', {
    default: () => [],
  });

  const { t } = useI18n();

  const selected = ref<HostInfo[]>([]);
  const bizId = window.PROJECT_CONFIG.BIZ_ID;
  const rules = [
    {
      message: t('请添加访问源'),
      trigger: 'change',
      validator: (value: string[]) => value.length > 0,
    },
  ];

  const handleChangeIP = (data: HostInfo[]) => {
    selected.value = data;
    sourceIps.value = data.map((item) => ({
      bk_biz_id: item.biz.id,
      bk_host_id: item.host_id,
      ip: item.ip,
    }));
  };

  const handleChangeWhitelist = (data: ServiceReturnType<typeof getWhitelist>['results']) => {
    // 避免与 handleChangeIP 同时修改 source_ips 参数
    nextTick(() => {
      const formatData = data.flatMap((item) => item.ips).map((ip) => ({ ip }));
      sourceIps.value.push(...formatData);
    });
  };

  defineExpose<Exposes>({
    init(data: HostInfo[]) {
      handleChangeIP(data);
    },
  });
</script>
