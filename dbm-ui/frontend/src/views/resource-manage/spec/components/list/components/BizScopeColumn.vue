<template>
  <BkTableColumn
    field="biz_scope"
    :label="t('应用范围')"
    show-overflow
    :width="300">
    <template #default="{ data }: { data: ResourceSpecModel }">
      <div
        v-if="data.biz_scope.length === 0"
        class="spec-list-biz-scope-column-all">
        <DbIcon
          class="all-icon"
          svg
          :type="BizScopesInfoMap[BizScopes.ALL].icon" />
        <span class="ml-4">{{ BizScopesInfoMap[BizScopes.ALL].label }}</span>
      </div>
      <div
        v-else
        class="spec-list-biz-scope-column-biz">
        <DbIcon
          class="biz-icon"
          svg
          :type="BizScopesInfoMap[BizScopes.BIZ].icon" />
        <span class="ml-4">{{ BizScopesInfoMap[BizScopes.BIZ].label }}</span>
        <div class="biz-name-list ml-4">
          （
          <span
            v-for="(item, index) in bizList(data)"
            :key="index">
            {{ item }}<span v-if="index !== bizList(data).length - 1">，</span>
          </span>
          ）
        </div>
      </div>
    </template>
  </BkTableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';

  import { useGlobalBizs } from '@stores';

  import { BizScopes, BizScopesInfoMap } from '../consts/bizScope';

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const bizList = (data: ResourceSpecModel) => data.biz_scope.map((bizId) => globalBizsStore.bizIdMap.get(bizId)?.name);
</script>

<style lang="less">
  .spec-list-biz-scope-column-all {
    display: flex;
    align-items: flex-start;

    .all-icon {
      margin-top: 4px;
      font-size: 16px;
      flex-shrink: 0;
    }
  }

  .spec-list-biz-scope-column-biz {
    display: flex;
    align-items: flex-start;

    .biz-icon {
      margin-top: 4px;
      font-size: 16px;
      flex-shrink: 0;
    }

    .biz-name-list {
      display: flex;
      flex-wrap: wrap;
    }
  }
</style>
