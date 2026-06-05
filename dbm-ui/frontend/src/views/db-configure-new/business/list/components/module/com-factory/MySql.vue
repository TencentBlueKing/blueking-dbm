<template>
  <div class="module-info-bar">
    <span class="module-info-item">
      <span class="module-info-label">{{ t('ID') }}：</span>{{ moduleInfo.moduleId || '--' }}
    </span>
    <span class="module-info-item">
      <span class="module-info-label">{{ t('存储层版本') }}：</span>{{ moduleInfo.version || '--' }}
    </span>
    <span class="module-info-item">
      <span class="module-info-label">{{ t('字符集') }}：</span>{{ moduleInfo.charset || '--' }}
    </span>
    <RelatedClusters
      :related-cluster-count="moduleInfo.relatedClusterCount"
      :related-clusters="moduleInfo.relatedClusters" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ParameterConfigItem } from '@services/source/configs';

  import type { ModuleInfo } from '@views/db-configure-new/common/types';

  import RelatedClusters from '../components/RelatedClusters.vue';

  interface Props {
    moduleInfo: ModuleInfo;
  }

  defineProps<Props>();

  const { t } = useI18n();

  /** 解析配置项 - MySQL 解析通用字段并返回 */
  function parseConfig(confItems: ParameterConfigItem[]): Partial<ModuleInfo> {
    const result: Partial<ModuleInfo> = {};

    confItems.forEach((item) => {
      if (item.conf_name === 'db_version') {
        result.version = item.conf_value ?? '';
      } else if (item.conf_name === 'charset') {
        result.charset = item.conf_value ?? '';
      }
    });

    return result;
  }

  /** 获取重置后的字段值 */
  function getResetValues(): Partial<ModuleInfo> {
    return {
      charset: '',
      version: '',
    };
  }

  /** 暴露方法给父组件调用 */
  defineExpose({
    getResetValues,
    parseConfig,
  });
</script>

<style lang="less" scoped>
  .module-info-bar {
    display: flex;
    align-items: center;
    gap: 32px;
    padding: 12px 24px;
  }

  .module-info-item {
    display: inline-flex;
    align-items: center;
    font-size: 12px;
    line-height: 20px;
    white-space: nowrap;
  }
</style>
