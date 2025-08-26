<template>
  <div
    v-if="isLoading"
    class="rotate-loading ml-4"
    style="display: inline-block">
    <DbIcon
      svg
      type="sync-pending" />
  </div>
  <template v-else>
    <BkTag
      v-if="type === 'tag'"
      class="cluster-load-tag ml-4"
      :size="size"
      :theme="tagInfo.theme"
      type="stroke">
      <template #icon>
        <DbIcon :type="tagInfo.icon" />
      </template>
      {{ tagInfo.tagText }}
    </BkTag>
    <div v-else>
      {{ tagInfo.text }}
    </div>
  </template>
</template>

<script setup lang="ts">
  import BkTag from 'bkui-vue/lib/tag';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryClusterLoad } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';

  interface Props {
    clusterType: string;
    domain: string;
    size?: ComponentProps<typeof BkTag>['size'];
    type?: 'tag' | 'text';
  }

  const props = withDefaults(defineProps<Props>(), {
    type: 'tag',
  });

  const route = useRoute();
  const { t } = useI18n();

  const tagInfoMap: Record<
    string,
    {
      icon: string;
      tagText: string;
      text: string;
      theme: 'danger' | 'success';
    }
  > = {
    high: {
      icon: 'gaofuzai',
      tagText: t('高负载'),
      text: t('高 '),
      theme: 'danger',
    },
    low: {
      icon: 'difuzai',
      tagText: t('低负载'),
      text: t('低'),
      theme: 'success',
    },
  };

  const tagInfo = computed(() => {
    if (clusterLoadData.value) {
      const { high_load: highLoad } = clusterLoadData.value.cluster_load_status_map[props.domain];
      if (highLoad) {
        return tagInfoMap.high;
      }
    }
    return tagInfoMap.low;
  });

  const { data: clusterLoadData, loading: isLoading } = useRequest(
    (params) =>
      queryClusterLoad(params, {
        cache: route.name as string,
      }),
    {
      defaultParams: [
        {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type:
            props.clusterType === ClusterTypes.REDIS
              ? [
                  ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                  ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                  ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                  ClusterTypes.PREDIXY_REDIS_CLUSTER,
                ].join(',')
              : props.clusterType,
        },
      ],
      // pollingInterval: 10 * 1000,
    },
  );
</script>

<style lang="less">
  .cluster-load-tag {
    padding: 0 6px 0 4px !important;

    [class*='db-icon'] {
      display: inline !important;
      margin: 0 !important;
      color: unset !important;
    }
  }
</style>
