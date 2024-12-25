<template>
  <EditableTableColumn
    class="edit-spec-column"
    field="reduce_nodes"
    :label="t('缩容的 IP')"
    required
    :rules="rules"
    :width="300">
    <EditSelect
      v-model="modelValue"
      auto-focus
      class="select-box"
      :clearable="false"
      :disabled="disabled"
      filterable
      :input-search="false"
      multiple
      :placeholder="t('请选择IP')">
      <BkOption
        v-for="(item, index) in dataList"
        :id="item.ip"
        :key="index"
        v-bk-tooltips="{
          disabled: !optionDisabled,
          content: t('缩容后不能少于2台'),
          placement: 'top',
        }"
        :disabled="optionDisabled"
        :name="item.ip">
        <div class="spec-display">
          <DbStatus :theme="item.status === 'running' ? 'success' : 'danger'" />
          <span class="text-overflow">{{ item.ip }}</span>
          <span>{{ item.bk_city ? `(${item.bk_city})` : '' }}</span>
        </div>
      </BkOption>
    </EditSelect>
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import { Column as EditableTableColumn, Select as EditSelect } from '@components/editable-table/Index.vue';

  interface Props {
    disabled: boolean;
    affinity?: string;
    dataList?: MongodbModel['mongos'];
  }

  const props = withDefaults(defineProps<Props>(), {
    affinity: '',
    dataList: () => [],
    initList: () => [],
  });

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (list: string[]) => {
        if (props.affinity !== 'CROS_SUBZONE') {
          return true;
        }
        const zoneIdSet = new Set<number>();
        props.dataList.forEach((item) => {
          if (!list.includes(item.ip)) {
            // 未选中
            zoneIdSet.add(item.bk_sub_zone_id);
          }
        });
        return zoneIdSet.size > 1;
      },
      trigger: 'change',
      message: t('当前集群容灾要求跨机房'),
    },
  ];

  const optionDisabled = computed(() => props.dataList.length - modelValue.value.length < 3);
</script>
