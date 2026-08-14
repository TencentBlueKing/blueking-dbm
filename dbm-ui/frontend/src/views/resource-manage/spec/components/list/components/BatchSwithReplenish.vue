<template>
  <AuthTemplate
    action-id="spec_manage"
    :resource="dbType">
    <DbPopconfirm
      :confirm-handler="() => handleBatchUpdate()"
      :confirm-text="needReplenish ? t('开启') : t('停用')"
      :content="
        needReplenish
          ? t('开启后，当资源池主机数低于参考水位时，将自动补货至目标配置')
          : t('停用后，当资源池主机数低于资源水位时，不触发自动补货')
      "
      placement="top"
      :title="needReplenish ? t('批量开启自动补货') : t('批量停用自动补货')">
      <BkButton
        class="opration-button"
        :disabled="disabled"
        text>
        {{ needReplenish ? t('开启自动补货') : t('停用自动补货') }}
      </BkButton>
    </DbPopconfirm>
  </AuthTemplate>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { addSpecReplenishTag } from '@services/source/dbresourceSpec';

  import type { DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  interface Props {
    dataList: ResourceSpecModel[];
    dbType: DBTypes;
    needReplenish: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const disabled = computed(() => props.dataList.length === 0);

  const { runAsync: runAddSpecReplenishTag } = useRequest(addSpecReplenishTag, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const handleBatchUpdate = () =>
    runAddSpecReplenishTag({
      need_replenish: props.needReplenish,
      spec_ids: props.dataList.map((item) => item.spec_id),
    });
</script>
