<template>
  <div class="version-selector-wrapper">
    <DbSelect
      v-model="modelValue"
      class="item-input"
      :disabled="isAdjustApply"
      filterable
      :input-search="false"
      :loading="loading"
      :placeholder="placeholder">
      <DbOption
        v-for="(item, index) in dbVersionList"
        :key="item"
        :label="item"
        :value="item">
        <span>{{ item }}</span>
        <DbTag
          v-if="index === 0"
          class="ml-5"
          theme="success">
          {{ t('推荐') }}
        </DbTag>
      </DbOption>
    </DbSelect>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listPackages } from '@services/source/package';

  import { useTicketModifyState } from '@hooks';

  interface Props {
    dbType: string;
    placeholder?: string;
    queryKey: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();
  // 调整申请模式只放开资源申请条件，本项只读
  const isAdjustApply = Boolean(useTicketModifyState()?.isAdjustApply);

  const {
    data: dbVersionList,
    loading,
    run: fetchData,
  } = useRequest(listPackages, {
    manual: true,
    onSuccess(packageList) {
      // 已有值且仍在列表里时保留：回填的版本可能先于列表返回，不能被推荐版本覆盖
      if (packageList.length > 0 && !packageList.includes(modelValue.value)) {
        const defaultVersion = packageList[0];
        modelValue.value = defaultVersion;
      }
    },
  });

  watch(
    () => [props.queryKey, props.dbType],
    () => {
      fetchData({
        db_type: props.dbType,
        query_key: props.queryKey,
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
      width: 522px;
    }
  }
</style>
