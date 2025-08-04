<template>
  <AuthTemplate
    action-id="spec_update"
    class="mr-8"
    :resource="dbType">
    <DbPopconfirm
      :confirm-handler="() => handleBatchUpdate()"
      :hide-on-click="false"
      placement="bottom"
      :title="t('批量修改应用范围')"
      :width="430">
      <BkButton
        v-bk-tooltips="{
          content: t('请选择规格'),
          disabled: !disabled,
        }"
        :disabled="disabled">
        {{ t('修改应用范围') }}
      </BkButton>
      <template #content>
        <BkRadioGroup
          v-model="bizScope"
          class="batch-edit-biz-scope mt-4">
          <BkRadio
            v-for="item in BizScopesInfoList"
            :key="item.id"
            class="biz-scope-item"
            :label="item.id">
            <DbIcon
              svg
              :type="item.icon" />
            <span class="ml-4">{{ item.label }}</span>
          </BkRadio>
        </BkRadioGroup>
        <BizSelector
          v-if="bizScope === BizScopes.BIZ"
          v-model="selectBizList"
          class="mt-12"
          :popover-props="{
            zIndex: 1000000,
          }" />
      </template>
    </DbPopconfirm>
  </AuthTemplate>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { batchUpdateSpec } from '@services/source/dbresourceSpec';

  import type { DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  import { BizScopes, BizScopesInfoList } from '../consts/bizScope';

  import BizSelector from './common/BizSelector.vue';

  interface Props {
    dataList: ResourceSpecModel[];
    dbType: DBTypes;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const bizScope = ref(BizScopes.ALL);
  const selectBizList = ref<string[]>([]);

  const disabled = computed(() => props.dataList.length === 0);

  const { run: runUpdateResourceSpec } = useRequest(batchUpdateSpec, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const handleBatchUpdate = () => {
    runUpdateResourceSpec({
      biz_scope: bizScope.value === BizScopes.ALL ? [] : selectBizList.value.map((item) => Number(item)),
      spec_ids: props.dataList.map((item) => item.spec_id),
    });
  };
</script>

<style lang="less">
  .batch-edit-biz-scope {
    display: flex;
    flex-direction: column;

    .bk-radio {
      width: fit-content;
      margin-left: 0;
    }

    .biz-scope-item {
      &:not(:first-child) {
        margin-top: 8px;
      }

      .bk-radio-label {
        display: flex;
        align-items: center;
        margin-left: 8px;
      }

      .db-svg-icon {
        font-size: 20px;
      }
    }
  }
</style>
