<template>
  <div class="render-mysql-message">
    <table>
      <thead>
        <tr>
          <th v-for="(columnTitle, index) in headColumnList" :key="index">{{ columnTitle }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in data" :key="index">
          <td v-for="key in headColumnList" :key="key">{{ row[key] }}</td>
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

  const headColumnList = computed(() => props.data ? Object.keys(props.data[0]) : [])
</script>
<style lang="less">
  .render-mysql-message {
    width: 100%;
    color: #DCDEE5;
    font-weight: 400;
    line-height: 24px;
    overflow: auto;
    border: 1px solid transparent;
    border-left: none;
    margin: 5px 0;
    .dott-line();

    .dott-line {
      background: linear-gradient(#1a1a1a, #1a1a1a) padding-box,
      repeating-linear-gradient(-45deg, #1a1a1a 0, #1a1a1a 2px, #C4C6CC 0, #C4C6CC 8px);
    }

    table {
      width: 100%;
      // word-break:break-all;
      word-wrap:break-word;

      thead {
        border: 1px solid transparent;
        border-right: none;
        border-top: none;
        .dott-line();
      }
      
      tbody {
        // border-bottom: 1px solid transparent;
        border-left: 1px solid transparent;
        .dott-line();
      }

      td, th {
        font-weight: normal;
        max-width: 500px;
        text-align: left;
        padding-left: 8px;
      }
    }
  }
</style>