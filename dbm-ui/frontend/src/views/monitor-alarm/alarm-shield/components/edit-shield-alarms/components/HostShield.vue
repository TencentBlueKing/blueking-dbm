<template>
  <BkFormItem
    :label="t('屏蔽范围')"
    required>
    <BkRadioGroup
      v-model="rangeValue"
      :disabled="disabled"
      type="card">
      <BkRadioButton
        v-for="item in shieldRangeList"
        :key="item.label"
        :label="item.value">
        {{ item.label }}
      </BkRadioButton>
    </BkRadioGroup>
  </BkFormItem>
  <IpSelector
    v-if="rangeValue === 'partial'"
    :biz-id="bizId"
    :button-text="t('添加主机')"
    :data="hostList"
    :disable-tips="disabled ? t('编辑模式下不可更改') : ''"
    :is-cloud-area-restrictions="false"
    service-mode="all"
    @change="handleHostChange">
  </IpSelector>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type HostInfo } from '@services/types';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  interface Props {
    disabled?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const { t } = useI18n();

  const rangeValue = ref('partial');
  const hostList = ref<HostInfo[]>([]);

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const shieldRangeList = [
    {
      label: t('指定主机'),
      value: 'partial',
    },
    {
      label: t('业务全部主机'),
      value: 'all',
    },
  ];

  const handleHostChange = (hostList: HostInfo[]) => {
    console.log(hostList);
  };
</script>
