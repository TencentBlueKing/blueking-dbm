<template>
  <div class="version-selector-wrapper">
    <BkSelect
      v-model="modelValue"
      class="item-input"
      filterable
      :input-search="false"
      :loading="loading"
      :placeholder="placeholder">
      <BkOption
        v-for="(item, index) in dbVersionList"
        :key="item"
        :label="item"
        :value="item">
        <span>{{ item }}</span>
        <BkTag
          v-if="index === 0"
          class="ml-5"
          theme="success">
          {{ t('推荐') }}
        </BkTag>
      </BkOption>
    </BkSelect>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listPackages } from '@services/source/package';

  interface Props {
    queryKey: string;
    dbType: string;
    placeholder?: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const {
    data: dbVersionList,
    loading,
    run: fetchData,
  } = useRequest(listPackages, {
    manual: true,
  });

  watch(
    () => [props.queryKey, props.dbType],
    () => {
      fetchData({
        query_key: props.queryKey,
        db_type: props.dbType,
      });
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less">
  .version-selector-wrapper {
    position: relative;
    display: inline-block;

    .item-input {
      width: 435px;
    }
  }
</style>
