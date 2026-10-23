<template>
  <div class="render-mysql-message">
    <table v-if="rows.length > 0">
      <thead>
        <tr>
          <th
            v-for="(columnTitle, index) in headColumnList"
            :key="index">
            {{ columnTitle }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="index">
          <td
            v-for="key in headColumnList"
            :key="key">
            {{ formatValue(row[key]) }}
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else>{{ resultText }}</div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: unknown;
    rowsAffected?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    rowsAffected: undefined,
  });

  const { t } = useI18n();

  const rows = computed<Record<string, unknown>[]>(() => {
    if (!Array.isArray(props.data)) {
      return [];
    }
    const isTable = props.data.every((row: unknown) => typeof row === 'object' && row !== null && !Array.isArray(row));
    return isTable ? props.data as Record<string, unknown>[] : [];
  });
  const headColumnList = computed(() => rows.value[0] ? Object.keys(rows.value[0]) : []);
  const formatValue = (value: unknown) => {
    if (value === null) {
      return 'NULL';
    }
    return typeof value === 'object' ? JSON.stringify(value) : String(value ?? '');
  };
  const resultText = computed(() => {
    if (Array.isArray(props.data) && props.data.length === 0) {
      return t('WebConsole_查询结果为空');
    }
    if ((props.data === true || props.data === null || props.data === undefined) && props.rowsAffected !== undefined) {
      return t('WebConsole_命令执行成功');
    }
    return formatValue(props.data);
  });
</script>
<style lang="less">
  .render-mysql-message {
    width: 100%;
    margin: 5px 0;
    overflow: auto;
    font-weight: 400;
    line-height: 24px;
    color: #dcdee5;
    border: 1px solid transparent;
    border-left: none;
    .dott-line();

    .dott-line {
      background:
        linear-gradient(#1a1a1a, #1a1a1a) padding-box,
        repeating-linear-gradient(-45deg, #1a1a1a 0, #1a1a1a 2px, #c4c6cc 0, #c4c6cc 8px);
    }

    table {
      width: 100%;
      overflow-wrap: break-word;

      thead {
        border: 1px solid transparent;
        border-top: none;
        border-right: none;
        .dott-line();
      }

      tbody {
        border-left: 1px solid transparent;
        .dott-line();
      }

      td,
      th {
        max-width: 500px;
        padding-left: 8px;
        font-weight: normal;
        text-align: left;
      }
    }
  }
</style>
