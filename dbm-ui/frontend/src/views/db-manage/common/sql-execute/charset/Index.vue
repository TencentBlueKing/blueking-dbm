<template>
  <BkFormItem
    :label="t('字符集')"
    property="charset"
    required>
    <DbSelect
      v-model="modelValue"
      style="width: 360px">
      <DbOption
        v-for="item in charsetList"
        :key="item"
        :value="item">
        {{ item }}
      </DbOption>
    </DbSelect>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  interface Props {
    dbType?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const mysqlCharsetList = ['default', 'utf8mb4', 'utf8', 'latin1', 'gbk', 'gb2312'];
  const sqlserverCharsetList = ['GBK'];

  const charsetList = computed(() => (props.dbType === DBTypes.SQLSERVER ? sqlserverCharsetList : mysqlCharsetList));
</script>
