<template>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchSubscription'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchSubscriptionDisabled,
        content: t('仅可订阅状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchSubscriptionDisabled"
      text
      @click="showCreateSubscribeRuleSlider = true">
      {{ t('批量订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchAuthorize'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchAuthorizeDisabled,
        content: t('仅可授权状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchAuthorizeDisabled"
      text
      @click="clusterAuthorizeShow = true">
      {{ t('批量授权') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchAddTag'">
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchAddTag = true)">
      {{ t('添加标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchRemoveTag'">
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchRemoveTag = true)">
      {{ t('移除标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'mysql.haClusterList.disable'"
    @click="handleDisableCluster(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchDisabledDisabled,
        content: t('仅可禁用状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchDisabledDisabled"
      text
      @click="handleDisableCluster(selected)">
      {{ t('禁用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.enable'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchEnableDisabled,
        content: t('仅可启用状态为“已禁用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchEnableDisabled"
      text
      @click="handleEnableCluster(selected)">
      {{ t('启用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.delete'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchDeleteDisabled,
        content: t('仅可删除状态为“已禁用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchDeleteDisabled"
      text
      @click="handleDeleteCluster(selected)">
      {{ t('删除') }}
    </BkButton>
  </BkDropdownItem>
  <CreateSubscribeRuleSlider
    v-model="showCreateSubscribeRuleSlider"
    :selected-clusters="selected"
    show-tab-panel
    @success="handleSubscribeSuccess" />
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBHA, 'tendbhaSlave']"
    :selected="selected"
    @success="handleAuthorizeSuccess" />
  <ClusterBatchAddTag
    v-model:is-show="showClusterBatchAddTag"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :selected="selected"
    @success="handleSuccess" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbHaModel from '@services/model/mysql/tendbha';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import CreateSubscribeRuleSlider from '@views/db-manage/mysql/dumper/components/create-rule/Index.vue';

  interface Props {
    selected: TendbHaModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.TENDBHA,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const sideSliderShow = defineModel<boolean>('side-slider-show', {
    required: true,
  });

  const { t } = useI18n();
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBHA,
    {
      onSuccess: () => handleSuccess(),
    },
  );

  const showCreateSubscribeRuleSlider = ref(false);
  const clusterAuthorizeShow = ref(false);
  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);

  const batchSubscriptionDisabled = computed(() => props.selected.some((data) => data.isOffline));
  const batchAuthorizeDisabled = computed(() => props.selected.some((data) => data.isOffline));
  const batchDisabledDisabled = computed(() =>
    props.selected.some((data) => data.isOffline || Boolean(data.operationTicketId)),
  );
  const batchEnableDisabled = computed(() => props.selected.some((data) => data.isOnline || data.isStarting));
  const batchDeleteDisabled = computed(() =>
    props.selected.some((data) => data.isOnline || Boolean(data.operationTicketId)),
  );
  const isClusterTagEditable = computed(() =>
    props.selected.every((data) => data.permission[`${data.db_type}_edit` as keyof typeof data.permission]),
  );

  watch([showCreateSubscribeRuleSlider, clusterAuthorizeShow], () => {
    sideSliderShow.value = showCreateSubscribeRuleSlider.value || clusterAuthorizeShow.value;
  });

  const handleSuccess = () => {
    emits('success');
  };

  const handleSubscribeSuccess = () => {
    showCreateSubscribeRuleSlider.value = false;
    handleSuccess();
  };

  const handleAuthorizeSuccess = () => {
    clusterAuthorizeShow.value = false;
    handleSuccess();
  };
</script>
