<template>
  <div class="content-row">
    <div class="db-column">
      <DbNameTagInput ref="dbNameTagInputRef" />
    </div>
    <div class="table-column">
      <TableNameTagInput ref="tableNameTagInputref" />
    </div>
    <div class="operate-column">
      <div
        class="action-btn"
        @click="handleAppend">
        <DbIcon type="plus-fill" />
      </div>
      <div
        class="action-btn"
        :class="{
          disabled: removeable
        }"
        @click="handleRemove">
        <DbIcon type="minus-fill" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import DbNameTagInput from './DbNameTagInput.vue';
  import TableNameTagInput from './TableNameTagInput.vue';

  interface Props {
    removeable?: boolean;
  }

  interface Emits {
    (e: 'add'): void,
    (e: 'remove'): void,
  }

  interface Exposes {
    getValue: () => Promise<{
      db_name: string,
      table_names: string[],
    }>,
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const dbNameTagInputRef = ref<InstanceType<typeof DbNameTagInput>>();
  const tableNameTagInputref = ref<InstanceType<typeof TableNameTagInput>>();

  const handleAppend = () => {
    emits('add');
  };
  const handleRemove = () => {
    emits('remove');
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        dbNameTagInputRef.value!.getValue(),
        tableNameTagInputref.value!.getValue(),
      ]).then((data) => {
        const [dbName, tableNames] = data;
        return {
          db_name: dbName,
          table_names: tableNames,
        };
      });
    },
  });
</script>
<style lang="less" scoped>
  .content-row {
    display: flex;
    width: 100%;
    margin-bottom: 20px;

    .db-column {
      width: 360px;
    }

    .table-column {
      flex: 1;
      margin-left: 24px;
    }

    :deep(.render-db-name-scroll) {
      .bk-tag-input {
        top: 0;
      }

      .input-error {
        display: none;
      }
    }

    :deep(.bk-tag-input-trigger) {
      min-height: 32px;
      border-color: #C4C6CC;

      .placeholder {
        height: 32px !important;
        line-height: 32px !important;
      }

      .tag-list {
        height: 30px;
      }
    }

    .operate-column {
      display: flex;
      align-items: center;
      width: 84px;
      margin-left: 16px;

      .action-btn {
        display: flex;
        font-size: 14px;
        color: #979BA5;
        cursor: pointer;
        transition: all 0.15s;

        &:hover {
          color: #63656E;
        }

        &.disabled {
          color: #C4C6CC;
          cursor: not-allowed;
        }

        & ~ .action-btn {
          margin-left: 18px;
        }
      }
    }
  }
</style>
