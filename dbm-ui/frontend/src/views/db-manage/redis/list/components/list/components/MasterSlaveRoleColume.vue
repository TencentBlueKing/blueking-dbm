<template>
  <BaseRoleColumn
    v-bind="props"
    :min-width="280">
    <template #default="{ data }"> {{ data.ip }}:{{ data.port }}({{ data.seg_range }}) </template>
    <template #instanceList="{ clusterData }: { clusterData: RedisModel }">
      <BkTable :data="clusterData.redis_master">
        <BkTableColumn label="Master">
          <template #default="{ data }: { data: RedisModel['redis_master'][number] }">
            {{ data.instance }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="Slave">
          <template #default="{ rowIndex }: { rowIndex: number }">
            {{ clusterData.redis_slave[rowIndex]?.instance || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('分片')">
          <template #default="{ data }: { data: RedisModel['redis_master'][number] }">
            {{ data.seg_range || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
    </template>
  </BaseRoleColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { ClusterTypes } from '@common/const';

  import BaseRoleColumn, {
    type Props,
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  const props = defineProps<Props<ClusterTypes.REDIS, 'redis_master' | 'redis_slave'>>();

  const { t } = useI18n();
</script>
