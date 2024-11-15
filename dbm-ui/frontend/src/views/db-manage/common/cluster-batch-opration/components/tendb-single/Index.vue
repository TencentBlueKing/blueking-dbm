<template>
  <BkDropdownItem
    v-db-console="'mysql.singleClusterList.batchAuthorize'"
    @click="clusterAuthorizeShow = true">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchAuthorizeDisabled,
        content: t('仅可授权状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchAuthorizeDisabled"
      text>
      {{ t('批量授权') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'mysql.singleClusterList.disable'"
    @click="handleDisableCluster(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchDisabledDisabled,
        content: t('仅可禁用状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchDisabledDisabled"
      text>
      {{ t('禁用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'mysql.singleClusterList.enable'"
    @click="handleEnableCluster(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchEnableDisabled,
        content: t('仅可启用状态为“已禁用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchEnableDisabled"
      text>
      {{ t('启用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'mysql.singleClusterList.delete'"
    @click="handleDeleteCluster(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchDeleteDisabled,
        content: t('仅可删除状态为“已禁用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchDeleteDisabled"
      text>
      {{ t('删除') }}
    </BkButton>
  </BkDropdownItem>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBSINGLE]"
    :selected="selected"
    @success="handleAuthorizeSuccess" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbSingleModel from '@services/model/mysql/tendbsingle';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';

  interface Props {
    selected: TendbSingleModel[];
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const sideSliderShow = defineModel<boolean>('side-slider-show', {
    required: true,
  });

  defineOptions({
    name: ClusterTypes.TENDBSINGLE,
  });

  const { t } = useI18n();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBSINGLE,
    {
      onSuccess: () => handleSuccess(),
    },
  );

  const clusterAuthorizeShow = ref(false);

  const batchAuthorizeDisabled = computed(() => props.selected.some((data) => data.isOffline));
  const batchDisabledDisabled = computed(() => props.selected.some((data) => data.isOffline || data.operationDisabled));
  const batchEnableDisabled = computed(() => props.selected.some((data) => data.isOnline || data.isStarting));
  const batchDeleteDisabled = computed(() =>
    props.selected.some((data) => data.isOnline || Boolean(data.operationTicketId)),
  );

  watch(clusterAuthorizeShow, () => {
    sideSliderShow.value = clusterAuthorizeShow.value;
  });

  const handleSuccess = () => {
    emits('success');
  };

  const handleAuthorizeSuccess = () => {
    clusterAuthorizeShow.value = false;
    handleSuccess();
  };
</script>
