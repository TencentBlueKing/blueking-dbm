<template>
  <div
    :class="{
      'is-hover': isHover,
    }">
    <TextOverflowLayout>
      <AuthButton
        :action-id="viewActionId"
        :permission="Boolean(_.get(data.permission, viewActionId))"
        :resource="data.id"
        text
        theme="primary"
        @click="(event: MouseEvent) => handleToDetails(data.id, event)">
        <TextHighlight
          high-light-color="#F59500"
          :keyword="searchKeyword">
          {{ data.masterDomainDisplayName }}
        </TextHighlight>
      </AuthButton>
      <template #append>
        <slot
          name="append"
          v-bind="{ data: data }" />
        <CluterRelatedTicket
          v-if="data.operations.length > 0"
          class="ml-4"
          :data="data.operations"
          @toogle-show="handlePopoverShow" />
        <BkTag
          v-if="data.isOffline"
          class="ml-4"
          size="small"
          theme="warning"
          type="stroke">
          {{ t('已禁用') }}
        </BkTag>
        <BkTag
          v-if="data.isNew"
          class="ml-4"
          size="small"
          theme="success">
          NEW
        </BkTag>
        <div
          v-if="isSubscribed"
          v-bk-tooltips="t('查看告警订阅内容')"
          class="master-domain-alarm-sign"
          @click="(event: MouseEvent) => handleToDetails(data.id, event, 'alarmSubscription')">
          <DbIcon
            class="note-icon"
            type="note" />
        </div>
        <PopoverCopy @toogle-show="handlePopoverShow">
          <div @click="handleCopy(data.masterDomain)">
            {{ t('复制域名') }}
          </div>
          <div @click="handleCopy(data.masterDomainDisplayName)">
            {{ t('复制域名:端口') }}
          </div>
        </PopoverCopy>
      </template>
    </TextOverflowLayout>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { useAlarmSubscribe } from '@stores';

  import { ClusterTypes } from '@common/const';

  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import CluterRelatedTicket from '@views/db-manage/common/ClusterDetailRelatedTicket.vue';

  import { execCopy } from '@utils';

  import type { ClusterTypeRelateClusterModel, ISupportClusterType } from '../types';

  export interface Props {
    clusterType: ISupportClusterType;
    data: ValueOf<ClusterTypeRelateClusterModel>;
  }

  export interface Emits {
    (e: 'go-detail', id: number, event: MouseEvent, detailPanel?: string): void;
    (e: 'refresh'): void;
  }

  export interface Slots {
    append?: (params: { data: ValueOf<ClusterTypeRelateClusterModel> }) => VNode;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  defineSlots<Slots>();

  const viewActionIdMap: Record<ISupportClusterType, string> = {
    [ClusterTypes.DORIS]: 'doris_view',
    [ClusterTypes.ES]: 'es_view',
    [ClusterTypes.HDFS]: 'hdfs_view',
    [ClusterTypes.KAFKA]: 'kafka_view',
    [ClusterTypes.MONGO_REPLICA_SET]: 'mongodb_view',
    [ClusterTypes.MONGO_SHARED_CLUSTER]: 'mongodb_view',
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: 'oracle_view',
    [ClusterTypes.ORACLE_SINGLE_NONE]: 'oracle_view',
    [ClusterTypes.PULSAR]: 'pulsar_view',
    [ClusterTypes.REDIS]: 'redis_view',
    [ClusterTypes.REDIS_INSTANCE]: 'redis_view',
    [ClusterTypes.RIAK]: 'riak_view',
    [ClusterTypes.SQLSERVER_HA]: 'sqlserver_view',
    [ClusterTypes.SQLSERVER_SINGLE]: 'sqlserver_view',
    [ClusterTypes.TENDBCLUSTER]: 'tendbcluster_view',
    [ClusterTypes.TENDBHA]: 'mysql_view',
    [ClusterTypes.TENDBSINGLE]: 'mysql_view',
  };

  const { t } = useI18n();
  const route = useRoute();
  const { subscribedDomainInfo } = useAlarmSubscribe();

  const searchKeyword = ref('');

  const isHover = ref(false);
  const viewActionId = computed(() => viewActionIdMap[props.clusterType]);
  const isSubscribed = computed(() => subscribedDomainInfo.dataSet.has(props.data.master_domain));

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

  const handleToDetails = (id: number, event: MouseEvent, detailPanel?: string) => {
    event.preventDefault();
    event.stopPropagation();
    emits('go-detail', id, event, detailPanel);
    return false;
  };

  const handlePopoverShow = (value: boolean) => {
    isHover.value = value;
  };
</script>
<style lang="less">
  .master-domain-alarm-sign {
    display: flex;
    width: 16px;
    height: 16px;
    margin-left: 4px;
    font-size: 13px;
    color: #3a84ff;
    cursor: pointer;
    background: #f0f5ff;
    border: 1px solid #a3c5fd;
    border-radius: 2px;
    align-items: center;
    justify-content: center;

    &:hover {
      background: #cddffe;
    }

    .note-icon {
      margin: 0 !important;
    }
  }
</style>
