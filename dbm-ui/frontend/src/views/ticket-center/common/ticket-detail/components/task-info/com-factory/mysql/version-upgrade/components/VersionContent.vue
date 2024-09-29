<template>
  <div class="version-content">
    <div class="content-item">
      <div class="item-title">{{ t('数据库版本') }}：</div>
      <div class="item-content">
        {{ data.version }}
      </div>
    </div>
    <div class="content-item">
      <div class="item-title">{{ t('版本包文件') }}：</div>
      <div
        v-overflow-tips
        class="item-content">
        {{ data.package }}
      </div>
    </div>
    <div class="content-item">
      <div class="item-title">{{ t('字符集') }}：</div>
      <div class="item-content">
        {{ data.charSet }}
      </div>
    </div>
    <div class="content-item">
      <div class="item-title">{{ t('绑定模块') }}：</div>
      <div class="item-content">
        {{ data.moduleName }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      version: string;
      package: string;
      charSet: string;
      moduleName: string;
    };
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .version-content {
    display: flex;
    flex-direction: column;

    .content-item {
      display: flex;
      width: 100%;
      line-height: 20px;

      .item-title {
        width: 72px;
        text-align: right;
      }

      .item-content {
        flex: 1;
        display: flex;
        align-items: center;
        overflow: hidden;
      }
    }
  }
</style>
