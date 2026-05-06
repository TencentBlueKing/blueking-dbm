<template>
  <div class="basic-indo-main">
    <div class="effect-infos">
      <div class="item-main">
        <div class="item-title">{{ isSpecial ? t('标题') : t('风险名称') }}</div>
        <span class="colon-sign">:</span>
        <div class="value-main">
          <TextEdit
            :biz-id="data.bk_biz_id"
            :manage-permission="managePermission"
            :readonly="isRiskDone"
            :value="data.name"
            @change="(value) => handleDetailChange('name', value)" />
        </div>
      </div>
      <div
        v-if="!isSpecial"
        class="item-main">
        <div class="item-title">{{ t('业务影响') }}</div>
        <span class="colon-sign">:</span>
        <div
          class="value-main"
          style="margin-top: -2px">
          <BizInpactEdit
            :biz-id="data.bk_biz_id"
            :manage-permission="managePermission"
            :readonly="isRiskDone"
            :value="data.biz_inpact"
            @change="(value) => handleDetailChange('biz_inpact', value)" />
        </div>
      </div>
    </div>
    <div class="normal-info">
      <div class="item-title">{{ isSpecial ? t('涉及 DB') : t('影响 DB') }}</div>
      <span class="colon-sign">:</span>
      <div class="value-main">
        <DbEdit
          :biz-id="data.bk_biz_id"
          :manage-permission="managePermission"
          operate-type="select"
          :readonly="isRiskDone"
          :value="data.db_type"
          @change="(value) => handleDetailChange('db_type', value)" />
      </div>
    </div>
    <div class="normal-info mt-12">
      <div class="item-title">{{ isSpecial ? t('涉及集群') : t('影响集群') }}</div>
      <span class="colon-sign">:</span>
      <div class="value-main">
        <ClusterEdit
          :biz-id="data.bk_biz_id"
          :db-type="data.db_type"
          :manage-permission="managePermission"
          :readonly="isRiskDone"
          :value="data.inpact_cluster"
          @change="(value) => handleDetailChange('inpact_cluster', value)" />
      </div>
    </div>
    <div class="normal-info mt-12">
      <div class="item-title">{{ isSpecial ? t('具体要求') : t('风险描述') }}</div>
      <span class="colon-sign">:</span>
      <div class="value-main">
        <RichTextEdit
          :biz-id="data.bk_biz_id"
          :manage-permission="managePermission"
          :risk-id="data.id"
          :value="data.description"
          @update-success="() => emits('updateSuccess')" />
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
  import RichTextEdit from './components/RichTextEdit.vue';
  import TextEdit from './components/TextEdit.vue';

  interface Props {
    data?: RiskMemoDetailModel;
    isSpecial?: boolean;
    managePermission?: boolean;
  }

  type Emits = (e: 'updateSuccess') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({}) as RiskMemoDetailModel,
    isSpecial: false,
    managePermission: true,
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
    margin-top: 18px;
    font-size: 12px;

    .effect-infos {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      width: 100%;

      .item-main {
        display: flex;
        flex: 1;
        min-width: 500px;
        margin-bottom: 12px;

        .item-title {
          min-width: 56px;
          font-size: 12px;
          color: #4d4f56;
          text-align: right;
          margin-top: 2px;
        }

        .colon-sign {
          margin-top: 3px;
          margin-right: 8px;
          margin-left: 4px;
        }

        .value-main {
          overflow: hidden;
          flex: 1;
        }
      }
    }

    .normal-info {
      display: flex;
      width: 100%;

      .item-title {
        min-width: 56px;
        font-size: 12px;
        color: #4d4f56;
        text-align: right;
        margin-top: 2px;
      }

      .colon-sign {
        margin-top: 3px;
        margin-right: 8px;
        margin-left: 4px;
      }

      .value-main {
        flex: 1;
        overflow: hidden;
      }
    }
  }
</style>
