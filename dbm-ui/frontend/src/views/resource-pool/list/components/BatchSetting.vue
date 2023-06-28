<template>
  <BkDialog
    :is-show="isShow"
    :title="t('设置业务专用')">
    <div>
      <div class="mb-16">
        已选{{ data.length }}台主机
      </div>
      <DbForm form-type="vertical">
        <DbFormItem
          :label="t('专用业务')"
          required>
          <BkSelect :loading="isBizListLoading">
            <BkOption
              v-for="bizItem in bizList"
              :key="bizItem.bk_biz_id"
              :label="bizItem.display_name"
              :value="bizItem.bk_biz_id" />
          </BkSelect>
        </DbFormItem>
        <DbFormItem
          :label="t('专用 DB')"
          required>
          <BkSelect :loading="isDbTypeListLoading">
            <BkOption
              v-for="item in dbTypeList"
              :key="item.id"
              :label="item.name"
              :value="item.id" />
          </BkSelect>
        </DbFormItem>
      </DbForm>
    </div>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/common';
  import { fetchDbTypeList } from '@services/infras';

  interface Props {
    data: number[],
    isShow: boolean,
  }

  defineProps<Props>();

  const { t } = useI18n();

  const {
    data: bizList,
    loading: isBizListLoading,
  } = useRequest(getBizs);

  const {
    data: dbTypeList,
    loading: isDbTypeListLoading,
  } = useRequest(fetchDbTypeList);
</script>

