<template>
  <TextOverflowLayout>
    <BkButton
      v-if="data.instance_domain"
      text
      theme="primary"
      @click="(event: MouseEvent) => handleToDetails(data.cluster_id, event)">
      <TextHighlight
        high-light-color="#F59500"
        :keyword="searchKeyword">
        {{ data.instance_domain }}
      </TextHighlight>
    </BkButton>
    <span v-else>--</span>
    <template
      v-if="data.instance_domain"
      #append>
      <slot
        name="append"
        v-bind="{ data: data }" />
      <DbIcon
        class="ml-4 mt-2"
        role="table-cell-operation"
        type="copy"
        @click="handleCopy(data.instance_domain)" />
    </template>
  </TextOverflowLayout>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';

  import { ClusterTypes } from '@common/const';

  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { URL_CLUSTER_DETAIL_MEMO_KEY } from '@views/db-manage/common/cluster-details';

  import { execCopy } from '@utils';

  import type { ClusterTypeRelateInstanceModel } from '../types';

  export interface Props {
    clusterType: ClusterTypes.MONGO_REPLICA_SET | ClusterTypes.MONGO_SHARED_CLUSTER;
    data: MongodbInstanceModel;
  }

  export type Emits = (e: 'go-detail', id: number, event: MouseEvent, detailPanel?: string) => void;

  export interface Slots {
    append?: (params: { data: ValueOf<ClusterTypeRelateInstanceModel> }) => VNode;
  }

  const props = defineProps<Props>();
  defineSlots<Slots>();

  const infoMap: Record<
    Props['clusterType'],
    {
      routeName: string;
    }
  > = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      routeName: 'MongoDBReplicaSetDetail',
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      routeName: 'MongoDBSharedClusterDetail',
    },
  };

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const searchKeyword = ref('');

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
