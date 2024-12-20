<template>
  <div
    v-if="data"
    class="dbm-cluster-instance-count-tag">
    {{ data[clusterType][countField] }}
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { queryClusterInstanceCount } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';

  interface Props {
    clusterType: ClusterTypes;
    role: 'cluster' | 'instance';
  }

  const props = defineProps<Props>();

  const { data } = useRequest(queryClusterInstanceCount, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

  const countField = computed(() => (props.role === 'cluster' ? 'cluster_count' : 'instance_count'));
</script>
<style lang="less">
  .bk-menu {
    .bk-menu-item.is-active {
      .dbm-cluster-instance-count-tag {
        color: #3a84ff;
        background: #e1ecff;
        transition: all 0.1s;
      }
    }

    .bk-menu-submenu {
      &.is-opened {
        .submenu-header-content {
          .dbm-cluster-instance-count-tag {
            display: none;
          }
        }
      }
    }
  }

  .dbm-cluster-instance-count-tag {
    display: inline-block;
    height: 16px;
    padding: 0 8px;
    margin-left: 4px;
    font-size: 12px;
    line-height: 16px;
    color: #fff;
    background: #333a47;
    border-radius: 8px;
  }
</style>
