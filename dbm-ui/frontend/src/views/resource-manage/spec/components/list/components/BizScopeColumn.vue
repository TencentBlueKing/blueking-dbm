<template>
  <TableColumn
    col-key="biz_scope"
    show-overflow
    :title="t('应用范围')"
    :width="300">
    <template #default="{ row }: { row: ResourceSpecModel }">
      <div
        v-if="row.biz_scope.length === 0"
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
          :type="BizScopesInfoMap[BizScopes.BIZS].icon" />
        <span class="ml-4">{{ BizScopesInfoMap[BizScopes.BIZS].label }}</span>
        <div class="biz-name-list ml-4">
          （
          <span
            v-for="(item, index) in bizList(row)"
            :key="index">
            {{ item }}<span v-if="index !== bizList(row).length - 1">，</span>
          </span>
          ）
        </div>
      </div>
    </template>
  </TableColumn>
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
