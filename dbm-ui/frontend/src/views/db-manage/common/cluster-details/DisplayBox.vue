<template>
  <div class="cluster-detail-display-box">
    <div class="row-item">
      <div class="cluster-domain">
        {{ data.masterDomain }}
      </div>
      <RenderOperationTag
        v-for="(item, index) in data.operationTagTips"
        :key="index"
        class="ml-4"
        :data="item" />
      <slot />
    </div>
    <div class="row-item">
      <div class="item-label">{{ t('集群别名：') }}</div>
      <div>{{ data.cluster_alias || '--' }}</div>
      <div class="item-label ml-16">{{ t('地域：') }}</div>
      <div>{{ data.region || '--' }}</div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  interface Props {
    data: Pick<TendbhaModel, 'masterDomain' | 'cluster_alias' | 'region' | 'operationTagTips'>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .cluster-detail-display-box {
    padding: 16px 60px 16px 20px;
    font-size: 12px;
    line-height: 20px;
    color: #313238;
    background: #f0f1f5;

    .row-item {
      display: flex;
      align-items: center;
    }

    .cluster-domain {
      font-size: 16px;
      font-weight: 700;
      line-height: 24px;
      color: #313238;
    }

    .item-label {
      color: #979ba5;
    }
  }
</style>
