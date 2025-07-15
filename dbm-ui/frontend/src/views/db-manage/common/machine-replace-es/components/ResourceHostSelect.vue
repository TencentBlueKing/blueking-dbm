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
            v-if="hostItem.instance_num"
            class="data-row-edit-instance">
            <EditHostInstance
              :model-value="hostItem.instance_num"
              @change="(value) => handleInstanceNumChange(value, hostItem)" />
          </div>
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
      v-model:is-show="isShowSelector"
      :disable-host-method="disableHostMethod"
      :params="{
        for_bizs: [currentBizId, 0],
        resource_types: [DBTypes.ES, 'PUBLIC'],
      }"
      :selected="modelValue"
      @change="handleHostChange" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  import EditHostInstance from '@views/db-manage/common/big-data-host-table/es-host-table/components/EditHostInstance.vue';

  import type { TReplaceNode } from '../Index.vue';

  interface Props {
    data: TReplaceNode;
    disableHostMethod?: (params: IValue) => string | boolean;
    placehoderId: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<TReplaceNode['hostList']>({
    required: true,
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const isShowSelector = ref(false);

  const isClientNode = computed(() => props.data.role === 'es_client');

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleRemoveHost = (hostId: number) => {
    modelValue.value = modelValue.value.filter((item) => item.bk_host_id !== hostId);
  };

  const handleHostChange = (data: IValue[]) => {
    modelValue.value = data.map((hostItem) => {
      const item = {
        bk_biz_id: hostItem.dedicated_biz,
        bk_cloud_id: hostItem.bk_cloud_id,
        bk_disk: hostItem.bk_disk,
        bk_host_id: hostItem.bk_host_id,
        ip: hostItem.ip,
      };
      if (!isClientNode.value) {
        return Object.assign({}, item, {
          instance_num: 1,
        });
      }
      return item;
    });
  };

  const handleInstanceNumChange = (value: number, hostData: Props['data']['hostList'][0]) => {
    modelValue.value = modelValue.value.reduce(
      (result, item) => {
        if (item.bk_host_id === hostData.bk_host_id) {
          result.push({
            ...item,
            instance_num: Number(value),
          });
        } else {
          result.push(item);
        }
        return result;
      },
      [] as Props['data']['hostList'],
    );
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
