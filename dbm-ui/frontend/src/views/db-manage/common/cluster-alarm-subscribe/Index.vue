<template>
  <template v-if="isAbleSubscribe">
    <div
      v-if="isNotSubscribed"
      v-db-console="'redis.clusterManage.editAlarmSubscription'">
      <OperationBtnStatusTips
        :data="data"
        :disabled="!data.isOffline">
        <BkButton
          :disabled="data.isOffline"
          style="width: 100%; height: 32px"
          text
          @click="handleClickEdit">
          {{ t('设置告警订阅') }}
        </BkButton>
      </OperationBtnStatusTips>
    </div>
    <div
      v-else
      v-db-console="'redis.clusterManage.deleteAlarmSubscription'">
      <OperationBtnStatusTips
        :data="data"
        :disabled="!data.isOffline">
        <BkPopConfirm
          :content="t('删除操作无法撤回，请谨慎操作！')"
          placement="bottom-start"
          :title="t('确认删除该告警订阅？')"
          trigger="click"
          :width="280"
          @confirm="handleConfirmDelete">
          <BkButton
            :disabled="data.isOffline"
            style="width: 100%; height: 32px"
            text>
            {{ t('删除告警订阅') }}
          </BkButton>
        </BkPopConfirm>
      </OperationBtnStatusTips>
    </div>
  </template>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@stores';

  import { messageSuccess } from '@utils';

  import type { ClusterModel, ISupportClusterType } from '../cluster-table/types';

  export interface Props<clusterType extends ISupportClusterType> {
    data: { master_domain: string } & ClusterModel<clusterType>;
  }

  type Emits = (e: 'edit', value: MouseEvent) => void;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { initSubscribedDomainInfo, metricsMap, subscribedDomainInfo } = useAlarmSubscribe();

  const isAbleSubscribe = computed(() => metricsMap[props.data.cluster_type].list.length > 0);
  const isNotSubscribed = computed(() => !subscribedDomainInfo.dataSet.has(props.data.master_domain));

  const { run: deleteSubscribeRun } = useRequest(deleteSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('删除成功'));
      initSubscribedDomainInfo();
    },
  });

  const handleClickEdit = (e: MouseEvent) => {
    emits('edit', e);
  };

  const handleConfirmDelete = () => {
    const currentInfo = subscribedDomainInfo.dataList.find((item) => item.master_domain === props.data.master_domain);
    if (!currentInfo) {
      return;
    }

    deleteSubscribeRun({
      ids: [currentInfo.id],
    });
  };
</script>
