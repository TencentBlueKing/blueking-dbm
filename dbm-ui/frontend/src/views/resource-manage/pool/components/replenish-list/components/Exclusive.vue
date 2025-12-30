<template>
  <div
    v-if="isShow"
    class="replenish-exclusive">
    <div class="replenish-exclusive-title">
      {{
        t('【title】为空的主机不计入当前数量，涉及主机：', {
          title: t('操作系统'),
        })
      }}
    </div>
    <div class="replenish-exclusive-content">
      {{ data?.exclusive_machine.empty_os.join(', ') }}
    </div>
    <div class="replenish-exclusive-title">
      {{
        t('【title】为空的主机不计入当前数量，涉及主机：', {
          title: t('园区'),
        })
      }}
    </div>
    <div class="replenish-exclusive-content">
      {{ data?.exclusive_machine.empty_subzone.join(', ') }}
    </div>
    <div class="replenish-exclusive-title">
      {{
        t('【title】为空的主机不计入当前数量，涉及主机：', {
          title: t('城市'),
        })
      }}
    </div>
    <div class="replenish-exclusive-content">
      {{ data?.exclusive_machine.empty_city.join(', ') }}
    </div>
    <div class="replenish-exclusive-title">
      {{ t('不含【机型】的规格无法触发补货，涉及规格：') }}
    </div>
    <div class="replenish-exclusive-content">
      {{ data?.exclusive_spec.map((item) => item.spec_name).join(', ') }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ResourceWaterLevel } from '../hooks/use-fetch-data';

  interface Props {
    data: ResourceWaterLevel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShow = computed(() => {
    return (
      props.data?.exclusive_machine.empty_os.length > 0 ||
      props.data?.exclusive_machine.empty_subzone.length > 0 ||
      props.data?.exclusive_machine.empty_city.length > 0 ||
      props.data?.exclusive_spec.length > 0
    );
  });
</script>

<style lang="less" scoped>
  .replenish-exclusive {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-gap: 8px;
    padding: 8px 12px;
    font-size: 12px;
    background: #f0f1f5;
    border-radius: 2px;

    .replenish-exclusive-title {
      font-weight: 700;
      color: #313238;
      flex-shrink: 0;
    }
  }
</style>
