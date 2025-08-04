<template>
  <AuthTemplate
    action-id="spec_update"
    class="mr-8"
    :resource="dbType">
    <DbPopconfirm
      :confirm-handler="() => handleBatchUpdate()"
      :confirm-text="enable ? t('启用') : t('停用')"
      :content="
        enable
          ? t('启用后，所有场景均可使用，如：部署、扩容、迁移规格')
          : t('停用后，存量集群的变更操作不受影响，新增集群不可使用此规格')
      "
      placement="bottom"
      :title="enable ? t('批量启用规格') : t('批量停用规格')"
      :width="430">
      <BkButton
        v-bk-tooltips="{
          content: t('请选择规格'),
          disabled: !disabled,
        }"
        class="w-88"
        :disabled="disabled">
        {{ enable ? t('启用') : t('停用') }}
      </BkButton>
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

  interface Props {
    dataList: ResourceSpecModel[];
    dbType: DBTypes;
    enable: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

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
      enable: props.enable,
      spec_ids: props.dataList.map((item) => item.spec_id),
    });
  };
</script>
