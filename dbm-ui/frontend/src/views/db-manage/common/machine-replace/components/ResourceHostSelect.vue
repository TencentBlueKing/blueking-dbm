<template>
  <div class="replace-host-selector">
    <div
      v-show="data.hostList.length > 0"
      class="selector-value">
      <div>
        <div
          v-for="hostItem in data.hostList"
          :key="hostItem.bk_host_id"
          class="data-row">
          <div>{{ hostItem.ip }}</div>
          <div
            class="data-row-remve-btn"
            @click="handleRemoveHost(hostItem.bk_host_id)">
            <DbIcon type="close" />
          </div>
        </div>
      </div>
    </div>
    <div
      v-show="data.hostList.length < 1"
      class="selector-box">
      <BkButton @click="handleShowSelector">
        <i class="db-icon-add" />
        {{ t('添加服务器') }}
      </BkButton>
    </div>
    <Teleport :to="`#${placehoderId}`">
      <span
        v-if="data.hostList.length > 0"
        class="ip-edit-btn"
        @click="handleShowSelector">
        <DbIcon type="edit" />
      </span>
    </Teleport>
    <ResourceHostSelector
      v-model="modelValue"
      v-model:is-show="isShowSelector"
      :params="{
        for_bizs: [currentBizId, 0],
        resource_types: [dbType, 'PUBLIC'],
      }"
      :selected="modelValue" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  import type { TReplaceNode } from '../Index.vue';

  interface Props {
    data: TReplaceNode;
    dbType: string;
    placehoderId: string;
  }

  defineProps<Props>();

  const modelValue = defineModel<IValue[]>({
    required: true,
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const isShowSelector = ref(false);

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleRemoveHost = (hostId: number) => {
    modelValue.value = modelValue.value.filter((item) => item.bk_host_id !== hostId);
  };
</script>
<style lang="less" scoped>
  .replace-host-selector {
    font-size: 12px;
    color: #63656e;

    .selector-value {
      height: 100%;

      .data-row {
        display: flex;
        height: 42px;
        align-items: center;
        padding-left: 16px;

        & ~ .data-row {
          border-top: 1px solid #dcdee5;
        }

        &:hover {
          .data-row-remve-btn {
            opacity: 100%;
          }
        }
      }

      .data-row-remve-btn {
        display: flex;
        width: 52px;
        height: 100%;
        margin-left: auto;
        font-size: 16px;
        color: #3a84ff;
        cursor: pointer;
        opacity: 0%;
        transition: all 0.15s;
        justify-content: center;
        align-items: center;
      }
    }

    .selector-box {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }
  }
</style>
