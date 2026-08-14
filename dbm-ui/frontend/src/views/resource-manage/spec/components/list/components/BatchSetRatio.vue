<template>
  <AuthTemplate
    action-id="spec_manage"
    class="mr-8"
    :resource="dbType">
    <DbPopconfirm
      :confirm-handler="() => handleBatchUpdate()"
      :hide-on-click="false"
      placement="top"
      :title="t('批量修改参考水位')"
      :width="430">
      <BkButton
        class="opration-button"
        :disabled="disabled"
        text>
        {{ t('修改参考水位') }}
      </BkButton>
      <template #content>
        <BkInput
          v-model="ratioValue"
          style="width: 200px"
          suffix="%" />
      </template>
    </DbPopconfirm>
  </AuthTemplate>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { setSpecReplenishRatio } from '@services/source/dbresourceSpec';

  import type { DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  interface Props {
    dataList: ResourceSpecModel[];
    dbType: DBTypes;
    ratioMap?: Record<string, number>;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const ratioValue = ref(0);

  const disabled = computed(() => props.dataList.length === 0);

  const { runAsync: runSetSpecReplenishRatio } = useRequest(setSpecReplenishRatio, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  watch(
    () => props.ratioMap,
    () => {
      if (props.ratioMap) {
        ratioValue.value = props.ratioMap['default'] * 100;
      }
    },
    {
      immediate: true,
    },
  );

  const handleBatchUpdate = () =>
    runSetSpecReplenishRatio({
      ratio_map: props.dataList.reduce<Record<string, number>>((acc, item) => {
        Object.assign(acc, {
          [item.spec_id]: ratioValue.value / 100,
        });
        return acc;
      }, props.ratioMap || {}),
    });
</script>
