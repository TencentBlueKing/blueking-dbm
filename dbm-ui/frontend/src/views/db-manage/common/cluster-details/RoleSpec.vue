<template>
  <div class="clusster-role-spec-box">
    <div
      v-for="role in roleList"
      :key="role"
      class="role-item">
      <slot :name="role" />
      <div class="mr-4">:</div>
      <div
        v-for="(roleItem, index) in data[role]"
        :key="index">
        {{ roleItem.spec_config.name }}
        <I18nT keypath="_n台_">
          {{ roleItem.spec_config.count }}
        </I18nT>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts" generic="T extends string[]">
  import type { VNode } from 'vue';

  import type { ClusterListNode } from '@services/types';

  export interface Props<T extends string[]> {
    data: {
      [K in T[number]]: ClusterListNode[];
    };
    roleList: T;
  }

  export interface Slots<T extends string[]> {
    child: {
      [K in T[number]]: () => VNode[];
    };
  }

  defineProps<Props<T>>();
  defineSlots<Slots<T>['child']>();
</script>
<style lang="less">
  .clusster-role-spec-box {
    line-height: 20px;

    .role-item {
      display: flex;

      & ~ .role-item {
        margin-top: 8px;
      }
    }
  }
</style>
