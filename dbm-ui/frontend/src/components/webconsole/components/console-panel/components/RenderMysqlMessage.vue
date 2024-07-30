<template>
  <div class="render-mysql-message">
    <table>
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
          v-for="(row, index) in data"
          :key="index">
          <td
            v-for="key in headColumnList"
            :key="key">
            {{ row[key] }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    data: Record<string, string>[];
  }

  const props = defineProps<Props>();

  const headColumnList = computed(() => (props.data ? Object.keys(props.data[0]) : []));
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
      word-wrap: break-word;

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
