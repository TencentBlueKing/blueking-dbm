<template>
  <BkSideslider
    v-model:is-show="isShow"
    :width="900">
    <template #header>
      <span>{{ t('手动修改迁移的 DB 名') }}</span>
      <BkTag class="ml-8">{{ domain }}</BkTag>
    </template>
    <div class="edit-name-box">
      <ClusterDb v-bind="props" />
      <div style="margin-top: 24px; margin-bottom: 16px; font-size: 12px">
        <span style="font-weight: bold; color: #313238">{{ t('DB 列表') }}</span>
        <I18nT
          keypath="（共 n 个）"
          style="color: #63656e">
          {{ data.rename_infos.length }}
        </I18nT>
        <ExportBtn
          v-bind="props"
          class="ml-12" />
      </div>
      <RenameList v-bind="props" />
    </div>
    <template #footer>
      <BkButton
        class="w-88"
        theme="primary"
        @click="() => (isShow = false)">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import ClusterDb from './components/ClusterDb.vue';
  import ExportBtn from './components/ExportBtn.vue';
  import RenameList from './components/RenameList.vue';

  interface Props {
    data: TicketModel<Sqlserver.DataMigrate>['details']['infos'][number];
    domain: string;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', { default: false, required: true });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .edit-name-box {
    padding: 20px 24px;
  }
</style>
