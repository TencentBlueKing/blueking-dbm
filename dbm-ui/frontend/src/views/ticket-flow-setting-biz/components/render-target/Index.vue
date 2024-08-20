<template>
  <div class="append-config-target">
    <div
      v-if="showSelectClusters"
      class="line-box">
      <BkTag
        class="line-box-tag"
        theme="info">
        AND
      </BkTag>
    </div>
    <div class="select-box">
      <SelectBiz
        ref="selectBizRef"
        v-model="currentBizId"
        disabled
        @add="showSelectClusters = true"
        @change="handleChangeBizId" />
      <SelectClusters
        v-if="showSelectClusters"
        ref="selectClustersRef"
        v-model="selectedClusterIds"
        :biz-id="currentBizId"
        class="mt-20"
        :db-type="modelValue.dbType"
        @change="handleChangeClusterIds"
        @remove="showSelectClusters = false" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import SelectBiz from './components/SelectBiz.vue';
  import SelectClusters from './components/SelectClusters.vue';

  interface Exposes {
    getValue: () => Promise<{
      bk_biz_id: number;
      cluster_ids: number[];
    }>;
  }

  const modelValue = defineModel<{
    dbType: DBTypes;
    bizId: number;
    clusterIds: number[];
  }>({
    default: () => ({
      dbType: DBTypes.MYSQL,
      bizId: 0,
      clusterIds: [],
    }),
  });

  const selectBizRef = ref<InstanceType<typeof SelectBiz>>();
  const selectClustersRef = ref<InstanceType<typeof SelectClusters>>();
  const currentBizId = ref<number>(0);
  const selectedClusterIds = ref<number[]>([]);
  const showSelectClusters = ref(false);

  watch(
    modelValue,
    () => {
      currentBizId.value = modelValue.value.bizId;
      if (modelValue.value.clusterIds.length > 0) {
        showSelectClusters.value = true;
        selectedClusterIds.value = modelValue.value.clusterIds;
      }
    },
    {
      immediate: true,
    },
  );

  const handleChangeBizId = (value: number) => {
    currentBizId.value = value;
    selectedClusterIds.value = [];
  };

  const handleChangeClusterIds = (value: number[]) => {
    selectedClusterIds.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([selectBizRef.value?.getValue(), selectClustersRef.value?.getValue()]).then(
        ([bizId, clusterIds]) => ({
          bk_biz_id: bizId as number,
          cluster_ids: clusterIds as number[],
        }),
      );
    },
  });
</script>

<style lang="less">
  .append-config-target {
    position: relative;
    display: flex;
    align-items: center;

    .line-box {
      position: relative;
      width: 41px;
      height: 54px;
      border: 1px solid #c4c6cc;
      border-right: none;

      .line-box-tag {
        position: absolute;
        top: 50%;
        left: 0;
        transform: translate(-50%, -50%);
      }
    }

    .select-box {
      flex: 1;

      .target-form-item {
        position: relative;
        display: flex;

        .target-prefix {
          display: flex;
          width: 64px;
          height: 32px;
          padding-left: 8px;
          font-size: 12px;
          color: #63656e;
          background: #fafbfd;
          border: 1px solid #c4c6cc;
          border-right: none;
          border-radius: 2px 0 0 2px;
          align-items: center;
        }

        .target-select {
          flex: 1;
        }

        .error-icon {
          position: absolute;
          right: 70px;
          display: flex;
          height: 32px;
          font-size: 14px;
          color: #ea3636;
          align-items: center;
        }

        .action-box {
          display: flex;
          width: 40px;
          height: 32px;
          padding-left: 14px;
          align-items: center;

          .action-btn {
            display: flex;
            font-size: 14px;
            color: #c4c6cc;
            cursor: pointer;
            transition: all 0.15s;

            &:hover {
              color: #979ba5;
            }

            &.disabled {
              color: #dcdee5;
              cursor: not-allowed;
            }

            & ~ .action-btn {
              margin-left: 12px;
            }
          }
        }
      }
    }
  }
</style>
