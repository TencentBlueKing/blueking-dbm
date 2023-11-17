<template>
  <div class="openarea-create-config-rule">
    <div class="variable-box">
      <BkButton
        style="margin-bottom: 12px; margin-left: auto; font-size: 12px;"
        text
        theme="primary"
        @click="handleShowVariable">
        {{ t('变量') }}
      </BkButton>
    </div>
    <RenderData
      class="mt16">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :cluster-id="clusterId"
        :data="item"
        :removeable="tableData.length < 2"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderData>
  </div>
  <VariableBox v-model="isShowVariable" />
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import VariableBox from '../variable-box/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  interface Props {
    clusterId: number,
    data: IData[]
  }

  interface Exposes {
    getValue: () => Promise<Required<IData>[]>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>([]);
  const tableData = shallowRef<Array<IDataRow>>([]);

  const isShowVariable = ref(false);

  watch(() => props.data, () => {
    if (props.data.length < 1) {
      tableData.value = [createRowData({})];
    } else {
      tableData.value = props.data.map(item => createRowData(item));
    }
  }, {
    immediate: true,
  });

  const handleShowVariable = () => {
    isShowVariable.value = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(rowRefs.value.map(item => item.getValue()));
    },
  });

</script>
<style lang="less">
  .openarea-create-config-rule {
    display: block;

    .variable-box{
      display: flex;
      margin-top: -24px;
    }

    .action-btn{
      display: inline-flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all .15s;

      &:hover{
        color: #979ba5;
      }

      &.disbled{
        color: #dcdee5;
        cursor: not-allowed;
      }
    }
  }
</style>
