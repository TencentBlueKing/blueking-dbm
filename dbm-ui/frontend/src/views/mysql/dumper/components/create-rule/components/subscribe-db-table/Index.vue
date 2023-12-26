<template>
  <div class="subscribe-db-table">
    <div class="title-row">
      <div class="title-spot db-column">
        {{ t("库名") }}<span class="required" />
      </div>
      <div class="title-spot table-column">
        {{ t("表名") }}<span class="required" />
      </div>
    </div>
    <RenderRow
      v-for="(item, index) in tableData"
      :key="item"
      ref="rowRefs"
      :removeable="removeable"
      @add="() => handleAddRow(index)"
      @remove="() => handleDeleteRow(index)" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { random } from '@utils';

  import RenderRow from './render-row/Index.vue';

  interface Exposes {
    getValue: () => Promise<{
      db_name: string,
      table_names: string[],
    }[]>,
  }

  const { t } = useI18n();

  const tableData = ref<string[]>([random()]);
  const rowRefs = ref();

  const removeable = computed(() => tableData.value.length === 1);

  const handleAddRow = (index: number) => {
    tableData.value.splice(index + 1, 0, random());
  };

  const handleDeleteRow = (index: number) => {
    tableData.value.splice(index, 1);
  };

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all(rowRefs.value.map((item: {
        getValue: () => Promise<{
          db_name: string,
          table_names: string[],
        }>
      }) => item.getValue()));
    },
  });


</script>
<style lang="less" scoped>
.subscribe-db-table {
  display: flex;
  width: 100%;
  flex-direction: column;

  .db-column {
    width: 360px;
  }

  .table-column {
    flex: 1;
    margin-left: 24px;
  }

  .title-row {
    display: flex;
    width: 100%;
    height: 20px;
    margin-bottom: 6px;
    line-height: 12px;
  }
}
</style>
