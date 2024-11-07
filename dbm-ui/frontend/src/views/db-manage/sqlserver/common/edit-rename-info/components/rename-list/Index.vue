<template>
  <div class="sqlserver-manage-rollback-rename-info-box">
    <RenderTable>
      <RenderTableHeadColumn>
        {{ t('构造 DB 名称') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        {{ t('构造后 DB 名称（自动生成，可修改）') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        {{ t('已存在的 DB（可修改）') }}
      </RenderTableHeadColumn>
      <template #data>
        <RenderRow
          v-for="(item, index) in modelValue"
          :key="index"
          ref="rowRefs"
          :index="index"
          :target-cluster-id="targetClusterId"
          :whole-db-list="modelValue"
          @change="(value) => handleChange(value, index)" />
      </template>
      <template
        v-if="modelValue.length < 1"
        #empty>
        <BkException
          description="没有数据"
          scene="part"
          type="empty" />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import type { IValue } from '../../Index.vue';

  import RenderRow from './RenderRow.vue';

  interface Props {
    targetClusterId: number;
  }

  interface Expose {
    getValue: () => Promise<IValue[]>;
  }

  defineProps<Props>();

  const modelValue = defineModel<IValue[]>({
    default: () => [],
  });
  const { t } = useI18n();

  const rowRefs = ref<InstanceType<typeof RenderRow>[]>([]);

  const handleChange = (value: IValue, index: number) => {
    modelValue.value.splice(index, 1, value);
  };

  defineExpose<Expose>({
    getValue() {
      return Promise.all(rowRefs.value!.map((item) => item.getValue()));
    },
  });
</script>
<style lang="less">
  .sqlserver-manage-rollback-rename-info-box {
    .bk-vxe-table {
      .vxe-cell {
        padding: 0 !important;
      }

      .bk-form-content {
        margin-left: 0 !important;
      }
    }
  }
</style>
