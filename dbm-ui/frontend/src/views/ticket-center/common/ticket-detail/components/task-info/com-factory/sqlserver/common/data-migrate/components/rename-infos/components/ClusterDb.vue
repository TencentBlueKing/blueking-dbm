<template>
  <EditableTable
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <EditableColumn
        field="db_list"
        :label="t('迁移 DB 名')"
        :min-width="200"
        required>
        <EditableBlock :placeholder="t('--')">
          <BkTag
            v-for="db in item.db_list"
            :key="db">
            {{ db }}
          </BkTag>
        </EditableBlock>
      </EditableColumn>
      <EditableColumn
        field="ignore_db_list"
        :label="t('忽略 DB 名')"
        :min-width="200">
        <EditableBlock :placeholder="t('--')">
          <BkTag
            v-for="db in item.ignore_db_list"
            :key="db">
            {{ db }}
          </BkTag>
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

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => [props.data]);
</script>
