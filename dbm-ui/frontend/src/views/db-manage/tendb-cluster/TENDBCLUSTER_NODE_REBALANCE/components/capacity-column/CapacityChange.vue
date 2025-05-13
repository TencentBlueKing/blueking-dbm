<template>
  <DbSideslider
    :before-close="handleClose"
    :is-show="isShow"
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ t('选择集群目标方案_n', { n: cluster.master_domain }) }}
        <BkTag theme="info">
          {{ t('存储层 RemoteDB/DR 同时变更') }}
        </BkTag>
      </span>
    </template>
    <div
      v-if="cluster"
      class="capacity-change-main">
      <div class="spec-box mb-24">
        <div class="table">
          <div class="row">
            <div class="cell">{{ t('当前规格') }}： {{ cluster.cluster_spec?.spec_name || '--' }}</div>
            <div class="cell">{{ t('变更后规格') }}： {{ futureSpec.spec_name || '--' }}</div>
          </div>
          <div class="row">
            <div class="cell">{{ t('当前机器组数') }}： {{ cluster.machine_pair_cnt || '--' }}</div>
            <div class="cell">{{ t('变更后机器组数') }}： {{ futureSpec.machine_pair || '--' }}</div>
          </div>
          <div class="row">
            <!-- 前后没有改变，仅展示 -->
            <div class="cell">{{ t('当前集群分片数') }}： {{ cluster.cluster_shard_num }}</div>
            <div class="cell">{{ t('变更后集群分片数') }}： {{ cluster.cluster_shard_num || '--' }}</div>
          </div>
          <div class="row">
            <div class="cell">
              {{ t('当前容量') }}：
              <span
                v-if="cluster.cluster_capacity"
                class="text-bold">
                {{ cluster.cluster_capacity }} G
              </span>
              <span v-else>--</span>
            </div>
            <div class="cell">
              {{ t('变更后容量') }}： <span class="text-bold">{{ futureSpec.cluster_capacity }} G</span>
            </div>
          </div>
        </div>
      </div>
      <BkForm label-width="135">
        <ClusterSpecPlanSelector
          v-model="modelValue.spec_id"
          v-model:custom-spec-info="customSpecInfo"
          :cloud-id="cluster.bk_cloud_id"
          :cluster-shard-num="cluster.cluster_shard_num"
          cluster-type="tendbcluster"
          machine-type="backend"
          @change="handlePlanChange" />
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useBeforeClose } from '@hooks';

  import ClusterSpecPlanSelector, {
    type TicketSpecInfo,
  } from '@views/db-manage/common/cluster-spec-plan-selector/Index.vue';

  export type { TicketSpecInfo };

  interface Props {
    cluster: Pick<
      TendbClusterModel,
      | 'id'
      | 'master_domain'
      | 'bk_cloud_id'
      | 'cluster_capacity'
      | 'cluster_shard_num'
      | 'cluster_spec'
      | 'db_module_id'
      | 'machine_pair_cnt'
      | 'remote_shard_num'
      | 'disaster_tolerance_level'
    >;
  }

  defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
    required: true,
  });
  const modelValue = defineModel<TicketSpecInfo>({
    default: () => ({
      cluster_capacity: 0,
      machine_pair: 0,
      spec_id: 0,
      spec_name: '',
    }),
  });
  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const futureSpec = reactive<TicketSpecInfo>({
    cluster_capacity: 0,
    machine_pair: 0,
    spec_id: 0,
    spec_name: '',
  });
  const choosedSpecId = ref(-1);
  const customSpecInfo = reactive({
    count: 1,
    specId: '',
  });

  watch(isShow, () => {
    if (isShow.value) {
      choosedSpecId.value = modelValue.value.spec_id;
      Object.assign(futureSpec, modelValue.value);
      Object.assign(customSpecInfo, {
        count: modelValue.value.machine_pair,
        specId: modelValue.value.spec_id,
      });
    }
  });

  async function handleClose() {
    const result = await handleBeforeClose(choosedSpecId.value !== -1);
    if (!result) {
      return;
    }
    isShow.value = false;
  }

  const handlePlanChange = (specId: number, specData: TicketSpecInfo) => {
    choosedSpecId.value = specId;
    Object.assign(futureSpec, specData);
  };

  const handleConfirm = () => {
    modelValue.value = futureSpec;
    isShow.value = false;
  };
</script>
<style lang="less" scoped>
  .capacity-change-main {
    padding: 20px 40px;

    .spec-box {
      width: 100%;
      padding: 16px;
      font-size: 12px;
      line-height: 18px;
      background-color: #fafbfd;

      .table {
        display: table;
        width: 100%;
        border-collapse: separate;
        border-spacing: 8px 0;
        table-layout: fixed;

        .row {
          display: table-row;
        }

        .cell {
          display: table-cell;
          height: 18px;
          vertical-align: middle;

          .text-bold {
            font-weight: bold;
          }
        }
      }
    }
  }
</style>
