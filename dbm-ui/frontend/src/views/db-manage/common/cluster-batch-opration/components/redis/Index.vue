<template>
  <BkDropdownItem
    v-db-console="'redis.clusterManage.extractKey'"
    @click="handleShowExtract(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以提取 Key'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text>
      {{ t('提取Key') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'redis.clusterManage.deleteKey'"
    @click="handlShowDeleteKeys(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以删除 Key'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text>
      {{ t('删除Key') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'redis.clusterManage.backup'"
    @click="handleShowBackup(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以备份'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text>
      {{ t('备份') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'redis.clusterManage.dbClear'"
    @click="handleShowPurge(selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以清档'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text>
      {{ t('清档') }}
    </BkButton>
  </BkDropdownItem>
  <!-- 提取 keys -->
  <ExtractKeys
    v-model:is-show="extractState.isShow"
    :data="extractState.data"
    @success="handleExtractKeysSuccess" />
  <!-- 删除 keys -->
  <DeleteKeys
    v-model:is-show="deleteKeyState.isShow"
    :data="deleteKeyState.data"
    @success="handleDeleteKeysSuccess" />
  <!-- 备份 -->
  <RedisBackup
    v-model:is-show="backupState.isShow"
    :data="backupState.data"
    @success="handleBackupSuccess" />
  <!-- 清档 -->
  <RedisPurge
    v-model:is-show="purgeState.isShow"
    :data="purgeState.data"
    @success="handlePurgeSuccess" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { useShowBackup } from '@views/db-manage/common/redis-backup/hooks/useShowBackup';
  import RedisBackup from '@views/db-manage/common/redis-backup/Index.vue';
  import { useShowDeleteKeys } from '@views/db-manage/common/redis-delete-keys/hooks/useShowDeleteKeys';
  import DeleteKeys from '@views/db-manage/common/redis-delete-keys/Index.vue';
  import { useShowExtractKeys } from '@views/db-manage/common/redis-extract-keys/hooks/useShowExtractKeys';
  import ExtractKeys from '@views/db-manage/common/redis-extract-keys/Index.vue';
  import { useShowPurge } from '@views/db-manage/common/redis-purge/hooks/useShowPurge';
  import RedisPurge from '@views/db-manage/common/redis-purge/Index.vue';

  interface Props {
    selected: RedisModel[];
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
    name: ClusterTypes.REDIS,
  });

  const { t } = useI18n();
  const { state: extractState, handleShow: handleShowExtract } = useShowExtractKeys();
  const { state: deleteKeyState, handleShow: handlShowDeleteKeys } = useShowDeleteKeys();
  const { state: backupState, handleShow: handleShowBackup } = useShowBackup();
  const { state: purgeState, handleShow: handleShowPurge } = useShowPurge();

  const batchOperationDisabled = computed(() =>
    props.selected.some((data) => {
      if (!data.isOnline) {
        return true;
      }

      if (data.operations?.length > 0) {
        const operationData = data.operations[0];
        return ([TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_CLOSE] as string[]).includes(
          operationData.ticket_type,
        );
      }

      return false;
    }),
  );

  watch(
    () => [extractState.isShow, deleteKeyState.isShow, backupState.isShow, purgeState.isShow],
    () => {
      sideSliderShow.value = extractState.isShow || deleteKeyState.isShow || backupState.isShow || purgeState.isShow;
    },
  );

  const handleSucess = () => {
    emits('success');
  };

  const handleExtractKeysSuccess = () => {
    extractState.isShow = false;
    handleSucess();
  };

  const handleDeleteKeysSuccess = () => {
    deleteKeyState.isShow = false;
    handleSucess();
  };

  const handleBackupSuccess = () => {
    backupState.isShow = false;
    handleSucess();
  };

  const handlePurgeSuccess = () => {
    purgeState.isShow = false;
    handleSucess();
  };
</script>
