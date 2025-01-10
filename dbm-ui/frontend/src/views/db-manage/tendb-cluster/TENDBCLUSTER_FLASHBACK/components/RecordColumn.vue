<template>
  <Column
    :description="t('通过列与列值确定记录')"
    :disabled-method="disabledMethod"
    field="rows_filter"
    :label="t('待闪回的记录')"
    :min-width="380"
    required
    :rules="rules">
    <EditTextarea v-model="modelValue" />
    <template #tips>
      <div class="tendbcluster-flashback-record-tips">
        <div style="font-weight: 700">{{ t('待闪回的记录') }}：</div>
        <div>
          <span>{{ t('填写示例：') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('字段名： field_A，field_B…，多个字段逗号分隔') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('字段值 1：va1_A, va1_B…，多个值逗号分隔') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('字段值 2：va2_A, va2_B…，') }}</span>
        </div>
        <div class="mt-10">
          <span>{{ t("如下示例，表示闪回 id=100 and name = 'zhangsan' 的记录") }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('id, name') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('100 ,zhangsan') }}</span>
        </div>
      </div>
    </template>
  </Column>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { Column, Textarea as EditTextarea } from '@components/editable-table/Index.vue';

  interface Props {
    clusterId?: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const disabledMethod = () => (props.clusterId ? false : t('请先选择集群'));

  const modelValue = defineModel<string>();

  const rules = [
    {
      validator: (value: string) => {
        const lineList = value.split('\n');
        if (lineList.length < 2) {
          return false;
        }
        const columnCount = lineList[0].split(',').length;
        return _.every(lineList, (lineItem) => lineItem.split(',').length === columnCount);
      },
      message: t('待闪回的记录格式不正确'),
      trigger: 'blur',
    },
  ];
</script>
<style lang="less">
  .tendbcluster-flashback-record-tips {
    div {
      display: flex;
      align-items: center;

      .circle-dot {
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-right: 6px;
        background-color: #63656e;
        border-radius: 50%;
      }
    }
  }
</style>
