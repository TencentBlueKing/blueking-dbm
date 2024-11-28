<template>
  <BkFormItem
    :label="t('源客户端 IP')"
    property="ips"
    required
    :rules="rules">
    <BatchInput
      v-model="modelValue"
      icon-type="batch-host-select"
      :max-count="50"
      @change="handleChange"
      @icon-click="() => (hostSelectorShow = true)" />
  </BkFormItem>
  <IpSelector
    v-model:show-dialog="hostSelectorShow"
    :biz-id="bizId"
    button-text=""
    :data="selectedHosts"
    :disable-dialog-submit-method="disableHostSubmitMethod"
    :is-cloud-area-restrictions="false"
    :panel-list="['staticTopo', 'manualInput', 'dbmWhitelist']"
    service-mode="all"
    :show-view="false"
    @change="handleChangeIP"
    @change-whitelist="handleChangeWhitelist">
    <template #submitTips="{ hostList: resultHostList }">
      <I18nT
        keypath="至多n台_已选n台"
        style="font-size: 14px; color: #63656e"
        tag="span">
        <span
          class="number"
          style="color: #2dcb56">
          50
        </span>
        <span
          class="number"
          style="color: #3a84ff">
          {{ resultHostList.length }}
        </span>
      </I18nT>
    </template>
  </IpSelector>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getWhitelist } from '@services/source/whitelist';
  import type { HostInfo } from '@services/types';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BatchInput from './components/BatchInput.vue';

  interface Emits {
    (e: 'change'): void;
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const rules = [
    {
      required: true,
      message: t('源客户端 IP 不能为空'),
      validator: (value: string) => value !== '',
    },
    {
      message: t('格式错误'),
      validator: (value: string) => {
        const ipList = value.split(batchSplitRegex);
        return ipList.every((ip) => ipv4.test(ip) || value.includes('%'));
      },
    },
    {
      message: t('最多输入n个', { n: 50 }),
      validator: (value: string) => {
        const ipList = value.split(batchSplitRegex);
        return ipList.length <= 50;
      },
    },
  ];

  const hostSelectorShow = ref(false);
  const selectedHosts = ref<HostInfo[]>([]);

  const disableHostSubmitMethod = (hostList: HostInfo[]) => (hostList.length <= 50 ? false : t('至多n台', { n: 50 }));

  const handleChange = () => {
    emits('change');
  };

  const handleChangeIP = (data: HostInfo[]) => {
    selectedHosts.value = data;
    modelValue.value = data.map((item) => item.ip).join(' | ');
  };

  const handleChangeWhitelist = (data: ServiceReturnType<typeof getWhitelist>['results']) => {
    // 避免与 handleChangeIP 同时修改 source_ips 参数
    nextTick(() => {
      const ipList = data.flatMap((item) => item.ips).map((ip) => ip);
      const prevIpList = modelValue.value ? modelValue.value.split(' | ') : [];
      modelValue.value = [...prevIpList, ...ipList].map((item) => item).join(' | ');
      emits('change');
    });
  };
</script>
