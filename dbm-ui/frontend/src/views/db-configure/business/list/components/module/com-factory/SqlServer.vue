<template>
  <div class="module-info-bar">
    <!-- 第一排 -->
    <div class="module-info-row">
      <span class="module-info-item">
        <span class="module-info-label">{{ t('ID') }}：</span>{{ moduleInfo.moduleId || '--' }}
      </span>
      <span class="module-info-item">
        <span class="module-info-label">{{ t('数据库版本') }}：</span>{{ moduleInfo.version || '--' }}
      </span>
      <span class="module-info-item">
        <span class="module-info-label">{{ t('主从方式') }}：</span>{{ haModeText || '--' }}
      </span>
      <span class="module-info-item">
        <span class="module-info-label">{{ t('字符集') }}：</span>{{ moduleInfo.charset || '--' }}
      </span>
    </div>
    <!-- 第二排 -->
    <div class="module-info-row">
      <span class="module-info-item">
        <span class="module-info-label">{{ t('操作系统版本') }}：</span>{{ moduleInfo.systemVersion || '--' }}
      </span>
      <span class="module-info-item">
        <span class="module-info-label">{{ t('内存分片比率') }}：</span>
        {{ moduleInfo.bufferPercent ? `${moduleInfo.bufferPercent}%` : '--' }}
      </span>
      <span class="module-info-item">
        <span class="module-info-label">{{ t('最大OS保留内存') }}：</span>
        {{ moduleInfo.maxRemainMemGb ? `${moduleInfo.maxRemainMemGb} GB` : '--' }}
      </span>
      <RelatedClusters
        :cluster-type="clusterType"
        :related-cluster-count="moduleInfo.relatedClusterCount"
        :related-cluster-list="moduleInfo.relatedClusterList"
        :related-clusters="moduleInfo.relatedClusters" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ParameterConfigItem } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import type { ModuleInfo } from '@views/db-configure/common/types';

  import RelatedClusters from '../components/RelatedClusters.vue';

  interface Props {
    clusterType?: ClusterTypes;
    moduleInfo: ModuleInfo;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  /** 解析配置项 - SqlServer 解析通用字段和特有字段并返回 */
  function parseConfig(confItems: ParameterConfigItem[]): Partial<ModuleInfo> {
    const result: Partial<ModuleInfo> = {};

    confItems.forEach((item) => {
      if (item.conf_name === 'db_version') {
        result.version = item.conf_value ?? '';
      } else if (item.conf_name === 'charset') {
        result.charset = item.conf_value ?? '';
      } else if (item.conf_name === 'system_version') {
        // SqlServer 操作系统版本
        result.systemVersion = item.conf_value ?? '';
      } else if (item.conf_name === 'buffer_percent') {
        // SqlServer 内存分片比率
        result.bufferPercent = item.conf_value ?? '';
      } else if (item.conf_name === 'max_remain_mem_gb') {
        // SqlServer 最大OS保留内存
        result.maxRemainMemGb = item.conf_value ?? '';
      } else if (item.conf_name === 'sync_type') {
        // SqlServer 主从方式
        result.syncType = item.conf_value ?? '';
      }
    });

    return result;
  }

  /** 获取重置后的字段值 */
  function getResetValues(): Partial<ModuleInfo> {
    return {
      bufferPercent: '',
      charset: '',
      maxRemainMemGb: '',
      syncType: '',
      systemVersion: '',
      version: '',
    };
  }

  /** 暴露方法给父组件调用 */
  defineExpose({
    getResetValues,
    parseConfig,
  });

  /** 主从方式映射 */
  const haModeMap: Record<string, string> = {
    always_on: 'Always On',
    mirroring: t('镜像'),
  };

  /** 主从方式显示文本 */
  const haModeText = computed(() => {
    if (!props.moduleInfo.syncType) return '--';
    return haModeMap[props.moduleInfo.syncType] || props.moduleInfo.syncType;
  });
</script>

<style lang="less" scoped>
  .module-info-bar {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px 24px;
  }

  .module-info-row {
    display: flex;
    align-items: center;
    gap: 32px;
    flex-wrap: wrap;
  }

  .module-info-item {
    display: inline-flex;
    align-items: center;
    font-size: 12px;
    line-height: 20px;
    white-space: nowrap;
  }
</style>
