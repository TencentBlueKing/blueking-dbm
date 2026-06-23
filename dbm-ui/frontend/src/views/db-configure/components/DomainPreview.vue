<template>
  <div class="domain-preview ml-12">
    <span>{{ t('集群域名预览') }}：</span>
    <div class="domain-preview-list">
      <!-- 主域名 / 单节点域名 -->
      <span>
        <span class="domain-module-name">{{ props.moduleName }}db</span>.<BkTag>{{ t('{集群名}') }}</BkTag> .{{
          bizName
        }}.db
        <BkTag v-if="isHaType">
          {{ t('主') }}
        </BkTag>
      </span>
      <!-- 从域名（仅主从类型显示） -->
      <span v-if="isHaType">
        <span class="domain-module-name">{{ props.moduleName }}dr</span>.<BkTag>{{ t('{集群名}') }}</BkTag> .{{
          bizName
        }}.db
        <BkTag>{{ t('从') }}</BkTag>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  interface Props {
    moduleName?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    moduleName: '',
  });

  const { t } = useI18n();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  /** 当前集群类型（从路由参数获取） */
  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);

  /** 业务代号（从 globalBizsStore 中根据 BIZ_ID 查找 english_name） */
  const bizName = computed(() => {
    const bizId = window.PROJECT_CONFIG.BIZ_ID;
    const biz = globalBizsStore.bizs.find((item) => item.bk_biz_id === bizId);
    return biz?.english_name ?? 'dba';
  });

  /** 是否为主从类型（需要显示从域名） */
  const isHaType = computed(() => {
    const haTypes = [ClusterTypes.TENDBHA, ClusterTypes.SQLSERVER_HA];
    return haTypes.includes(clusterType.value);
  });
</script>

<style lang="less" scoped>
  .domain-preview {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    white-space: nowrap;
  }

  .domain-preview-list {
    display: flex;
    gap: 16px;
  }

  .domain-module-name {
    color: #3a84ff;
  }
</style>
