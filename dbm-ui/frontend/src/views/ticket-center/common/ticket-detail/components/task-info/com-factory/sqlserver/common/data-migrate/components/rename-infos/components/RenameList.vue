<template>
  <EditableTable
    ref="table"
    class="mb-20"
    :model="data.rename_infos">
    <EditableRow
      v-for="(item, index) in data.rename_infos"
      :key="index">
      <EditableColumn
        field="db_name"
        :label="t('迁移 DB 名称')"
        :min-width="200"
        required>
        <EditableBlock>
          {{ item.db_name || '--' }}
        </EditableBlock>
      </EditableColumn>
      <EditableColumn
        field="target_db_name"
        :label="t('迁移后 DB 名称')"
        :min-width="200">
        <EditableBlock
          :class="{
            'is-change': item.target_db_name !== item.db_name,
          }">
          {{ item.target_db_name || '--' }}
        </EditableBlock>
      </EditableColumn>
      <EditableColumn
        field="rename_db_name"
        :label="t('已存在的 DB')"
        :min-width="200">
        <EditableBlock
          :class="{
            'is-change': !!item.rename_db_name,
          }">
          {{ item.rename_db_name || '--' }}
        </EditableBlock>
      </EditableColumn>
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  interface Props {
    data: TicketModel<Sqlserver.DataMigrate>['details']['infos'][number];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .is-change {
    background: #fff8e9;
  }
</style>
