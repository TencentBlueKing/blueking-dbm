<template>
  <template v-if="isAbleSubscribe">
    <BkDropdownItem
      v-if="isNotSubscribed"
      v-db-console="`${dbConsolePrefix}.editAlarmSubscription`">
      <OperationBtnStatusTips
        :data="data"
        :disabled="!data.isOffline">
        <AuthButton
          :action-id="permissionId"
          :class="{ 'is-dropdown-button': isDropdown }"
          :disabled="data.isOffline"
          :permission="data.permission[permissionId]"
          :resource="data.id"
          text
          @click="handleClickEdit">
          {{ t('设置告警订阅') }}
        </AuthButton>
      </OperationBtnStatusTips>
    </BkDropdownItem>
    <BkDropdownItem
      v-else
      v-db-console="`${dbConsolePrefix}.deleteAlarmSubscription`">
      <OperationBtnStatusTips
        :data="data"
        :disabled="!data.isOffline">
        <BkButton
          :class="{ 'is-dropdown-button': isDropdown }"
          :disabled="data.isOffline"
          text
          @click="handleClickDelete">
          {{ t('删除告警订阅') }}
        </BkButton>
      </OperationBtnStatusTips>
    </BkDropdownItem>
  </template>
</template>
<script setup lang="tsx" generic="T extends ISupportClusterType">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@hooks';

  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  import { messageSuccess } from '@utils';

  import type { ClusterModel, ISupportClusterType } from '../cluster-table/types';

  export interface Props<clusterType extends ISupportClusterType> {
    data: { master_domain: string } & ClusterModel<clusterType>;
    dbConsolePrefix?: string;
    isDropdown?: boolean;
  }

  export interface Emits {
    (e: 'edit', value: MouseEvent): void;
    (e: 'click'): void;
  }

  const props = withDefaults(defineProps<Props<T>>(), {
    dbConsolePrefix: '',
    isDropdown: false,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { initSubscribedDomainInfo, metricsMap, subscribedDomainInfo } = useAlarmSubscribe();

  const isAbleSubscribe = computed(() => metricsMap.value[props.data.cluster_type]?.list.length > 0);
  const isNotSubscribed = computed(() => !subscribedDomainInfo.value.dataSet.has(props.data.master_domain));
  const permissionId = computed(() => `${props.data.db_type}_subscribe_monitor` as keyof typeof props.data.permission);

  const { run: deleteSubscribeRun } = useRequest(deleteSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('删除成功'));
      initSubscribedDomainInfo();
    },
  });

  const handleClickEdit = (e: MouseEvent) => {
    emits('click');
    emits('edit', e);
  };

  const handleClickDelete = () => {
    emits('click');
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('删除'),
      contentAlign: 'left',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onConfirm: handleConfirmDelete,
      subTitle: (
        <div style='background-color: #F5F7FA; padding: 8px 16px;'>
          <div class='mt-4'>{t('删除订阅将停止发送告警通知并删除配置，如有需要可再次订阅。')}</div>
        </div>
      ),
      theme: 'danger',
      title: t('确定删除该告警订阅？'),
    });
  };

  const handleConfirmDelete = () => {
    const currentInfo = subscribedDomainInfo.value.dataList.find(
      (item) => item.master_domain === props.data.master_domain,
    );
    if (!currentInfo) {
      return;
    }

    deleteSubscribeRun({
      ids: [currentInfo.id],
    });
  };
</script>

<style lang="less">
  .is-dropdown-button {
    width: auto !important;
    padding: 0 !important;
    margin-left: 16px;
  }
</style>
