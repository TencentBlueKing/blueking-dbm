<template>
  <div class="basic-indo-main">
    <div class="effect-infos">
      <div
        class="item-mian"
        style="width: 30%">
        <div class="item-title">{{ isSpecial ? t('标题') : t('风险名称') }}</div>
        <span class="mr-8 ml-4">:</span>
        <div class="value-main">
          <TextEdit
            :readonly="isRiskDone"
            :value="data.name"
            @change="(value) => handleDetailChange('name', value)" />
        </div>
      </div>
      <div
        class="item-mian ml-12 mr-12"
        style="width: 25%">
        <div class="item-title">{{ isSpecial ? t('涉及 DB') : t('影响 DB') }}</div>
        <span class="mr-8 ml-4">:</span>
        <div class="value-main">
          <DbEdit
            operate-type="select"
            :readonly="isRiskDone"
            :value="data.db_type"
            @change="(value) => handleDetailChange('db_type', value)" />
        </div>
      </div>
      <div
        v-if="!isSpecial"
        class="item-mian"
        style="width: 45%">
        <div class="item-title">{{ t('业务影响') }}</div>
        <span class="mr-8 ml-4">:</span>
        <div class="value-main">
          <BizInpactEdit
            :readonly="isRiskDone"
            :value="data.biz_inpact"
            @change="(value) => handleDetailChange('biz_inpact', value)" />
        </div>
      </div>
    </div>
    <div class="normal-info">
      <div class="item-title">{{ isSpecial ? t('具体要求') : t('风险描述') }}</div>
      <span class="mr-8 ml-4">:</span>
      <div class="value-main">
        <TextEdit
          :readonly="isRiskDone"
          text-area
          :value="data.description"
          @change="(value) => handleDetailChange('description', value)" />
      </div>
    </div>
    <div class="normal-info">
      <div class="item-title">{{ isSpecial ? t('涉及集群') : t('影响集群') }}</div>
      <span class="mr-8 ml-4">:</span>
      <div class="value-main">
        <ClusterEdit
          :biz-id="data.bk_biz_id"
          :db-type="data.db_type"
          :readonly="isRiskDone"
          :value="data.inpact_cluster"
          @change="(value) => handleDetailChange('inpact_cluster', value)" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RiskMemoDetailModel from '@services/model/risk-memo/risk-memo-detail';
  import { updateRiskMemo } from '@services/source/riskMemo';

  import { messageSuccess } from '@utils';

  import BizInpactEdit from './components/BizInpactEdit.vue';
  import ClusterEdit from './components/ClusterEdit.vue';
  import DbEdit from './components/DbEdit.vue';
  import TextEdit from './components/TextEdit.vue';

  interface Props {
    data?: RiskMemoDetailModel;
    isSpecial?: boolean;
  }

  type Emits = (e: 'updateSuccess') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({}) as RiskMemoDetailModel,
    isSpecial: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isRiskDone = computed(() => props.data.status === 'done');

  const { run: runUpdateRiskMemoRun } = useRequest(updateRiskMemo, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('更新成功'));
      emits('updateSuccess');
    },
  });

  const handleDetailChange = (key: string, value: string) => {
    const params = {
      id: props.data.id,
      [key]: value,
    };
    if (key === 'db_type') {
      Object.assign(params, {
        inpact_cluster: 'all',
      });
    }
    runUpdateRiskMemoRun(params);
  };
</script>
<style lang="less">
  .basic-indo-main {
    font-size: 12px;
    margin-top: 18px;
    .effect-infos {
      width: 100%;
      display: flex;

      .item-mian {
        display: flex;
        align-items: center;

        .item-title {
          color: #4d4f56;
          min-width: 48px;
          text-align: right;
        }

        .value-main {
          flex: 1;
          overflow: hidden;
        }
      }
    }

    .normal-info {
      width: 100%;
      display: flex;
      margin-top: 12px;
      align-items: center;

      .item-title {
        color: #4d4f56;
      }

      .value-main {
        flex: 1;
      }
    }
  }
</style>
