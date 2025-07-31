<template>
  <BkPopover
    :disabled="!errorList.length"
    placement="top"
    :popover-delay="0"
    theme="light">
    <template #content>
      <div class="query-access-results-status-popover">
        <div class="title-main">{{ statusInfo.displayStatusText }}（{{ errorList.length }}）</div>
        <div
          v-for="item in errorList"
          :key="item"
          class="ip-item">
          {{ item }}
        </div>
      </div>
    </template>
    <div class="query-access-results-status">
      <DbStatus :theme="statusInfo.statusTheme" />
      <span>{{ statusInfo.displayStatusText }}</span>
      <span
        v-if="errorList.length > 0"
        class="error-count">
        {{ errorList.length }}
      </span>
    </div>
  </BkPopover>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Props {
    errorList: string[];
    successList: string[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const statusInfo = computed(() => {
    const { errorList, successList } = props;
    let displayStatusText = '';
    let statusTheme = '';
    if (!errorList.length) {
      displayStatusText = t('全部成功');
      statusTheme = 'success';
    } else if (!successList.length) {
      displayStatusText = t('全部失败');
      statusTheme = 'danger';
    } else {
      displayStatusText = t('部分失败');
      statusTheme = 'warning';
    }

    return {
      displayStatusText,
      statusTheme,
    };
  });
</script>

<style lang="less">
  .query-access-results-status-popover {
    .title-main {
      height: 20px;
      font-weight: 700;
      color: #ea3636;
    }

    .ip-item {
      display: flex;
      height: 20px;
      color: #4d4f56;
      align-items: center;
    }
  }
</style>
