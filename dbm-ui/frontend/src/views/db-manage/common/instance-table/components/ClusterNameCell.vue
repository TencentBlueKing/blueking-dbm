<template>
  <TextOverflowLayout>
    <AuthButton
      :action-id="viewActionId"
      :permission="Boolean(_.get(data.permission, viewActionId))"
      :resource="data.id"
      text
      theme="primary"
      @click="(event: MouseEvent) => handleToDetails(data.cluster_id, event)">
      <TextHighlight
        high-light-color="#F59500"
        :keyword="searchKeyword">
        {{ data.cluster_name }}
      </TextHighlight>
    </AuthButton>
    <template #append>
      <slot
        name="append"
        v-bind="{ data: data }" />
      <DbIcon
        class="ml-4 mt-2"
        role="table-cell-operation"
        type="copy"
        @click="handleCopy(data.cluster_name)" />
    </template>
  </TextOverflowLayout>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { ClusterTypes } from '@common/const';

  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { URL_CLUSTER_DETAIL_MEMO_KEY } from '@views/db-manage/common/cluster-details';

  import { execCopy } from '@utils';

  import type { ClusterTypeRelateInstanceModel, ISupportClusterType } from '../types';

  export interface Props {
    clusterType: ISupportClusterType;
    data: ValueOf<ClusterTypeRelateInstanceModel>;
  }

  export type Emits = (e: 'go-detail', id: number, event: MouseEvent, detailPanel?: string) => void;

  export interface Slots {
    append?: (params: { data: ValueOf<ClusterTypeRelateInstanceModel> }) => VNode;
  }

  const props = defineProps<Props>();
  defineSlots<Slots>();

  const infoMap: Record<
    ISupportClusterType,
    {
      routeName: string;
      viewActionId: string;
    }
  > = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      routeName: 'MongoDBReplicaSetDetail',
      viewActionId: 'mongodb_view',
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      routeName: 'MongoDBSharedClusterDetail',
      viewActionId: 'mongodb_view',
    },
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: {
      routeName: 'OracleHaDetail',
      viewActionId: 'oracle_view',
    },
    [ClusterTypes.REDIS_CLUSTER]: {
      routeName: 'redisClusterDetail',
      viewActionId: 'redis_view',
    },
    [ClusterTypes.REDIS_INSTANCE]: {
      routeName: 'redisClusterHaDetail',
      viewActionId: 'redis_view',
    },
    [ClusterTypes.SQLSERVER_HA]: {
      routeName: 'SqlServerHaClusterDetail',
      viewActionId: 'sqlserver_view',
    },
    [ClusterTypes.TENDBCLUSTER]: {
      routeName: 'tendbClusterDetail',
      viewActionId: 'tendbcluster_view',
    },
    [ClusterTypes.TENDBHA]: {
      routeName: 'tendbHaDetail',
      viewActionId: 'mysql_view',
    },
  };

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const searchKeyword = ref('');

  const viewActionId = computed(() => infoMap[props.clusterType].viewActionId);

  watch(
    route,
    () => {
      searchKeyword.value = (route.query.domain as string) || '';
    },
    {
      immediate: true,
    },
  );

  const handleCopy = (data: string) => {
    execCopy(
      data,
      t('复制成功，共n条', {
        n: 1,
      }),
    );
  };

  const handleToDetails = (clusterId: number, event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    const { href } = router.resolve({
      name: infoMap[props.clusterType].routeName,
      params: {
        clusterId,
      },
      query: {
        [URL_CLUSTER_DETAIL_MEMO_KEY]: 'info',
      },
    });
    window.open(href);
    return false;
  };
</script>
