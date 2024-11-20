<template>
  <BkDialog
    :is-show="isShow"
    render-directive="if"
    :title="t('编辑资源归属')"
    width="600"
    @closed="handleCancel">
    <BkForm
      ref="formRef"
      class="mt-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('所属业务')"
        property="for_biz"
        required>
        <BkSelect
          v-model="formData.for_biz"
          :allow-empty-values="[0]">
          <BkOption
            v-for="bizItem in bizList"
            :key="bizItem.bk_biz_id"
            :label="bizItem.display_name"
            :value="bizItem.bk_biz_id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('所属DB')"
        property="resource_type"
        required>
        <BkSelect v-model="formData.resource_type">
          <BkOption
            v-for="item in dbTypeList"
            :key="item.id"
            :label="item.name"
            :value="item.id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('资源标签')"
        property="labels">
        <TagSelector
          v-model="formData.labels"
          :bk-biz-id="formData.for_biz"
          :default-list="editData.labels"
          :disabled="!formData.for_biz && formData.for_biz !== 0" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        :loading="isUpdating"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { getBizs } from '@services/source/cmdb';
  import { updateResource } from '@services/source/dbresourceResource';
  import { fetchDbTypeList } from '@services/source/infras';
  import type { BizItem } from '@services/types';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  interface Props {
    editData: DbResourceModel;
  }

  interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const formRef = useTemplateRef('formRef');

  const formData = reactive({
    for_biz: 0,
    resource_type: '',
    labels: [] as DbResourceModel['labels'][number]['id'][],
  });
  const bizList = shallowRef<ServiceReturnType<typeof getBizs>>([]);
  const dbTypeList = shallowRef<ServiceReturnType<typeof fetchDbTypeList>>([]);

  watch(
    () => props.editData,
    () => {
      if (!Object.keys(props.editData).length) {
        return;
      }
      formData.for_biz = props.editData.for_biz.bk_biz_id;
      formData.resource_type = props.editData.resource_type;
      formData.labels = props.editData.labels.map((item) => item.id);
    },
    {
      immediate: true,
      deep: true,
    },
  );

  useRequest(getBizs, {
    onSuccess(data) {
      bizList.value = [
        {
          bk_biz_id: 0,
          display_name: t('公共资源池'),
        } as BizItem,
        ...data,
      ];
    },
  });

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      dbTypeList.value = [
        {
          id: 'PUBLIC',
          name: t('通用'),
        },
        ...data,
      ];
    },
  });

  const { loading: isUpdating, run: runUpdate } = useRequest(updateResource, {
    manual: true,
    onSuccess() {
      emits('refresh');
      isShow.value = false;
    },
  });

  const handleSubmit = async () => {
    await formRef.value!.validate();
    runUpdate({
      bk_host_ids: [props.editData.bk_host_id],
      for_biz: Number(formData.for_biz),
      resource_type: formData.resource_type,
      labels: formData.labels,
      rack_id: '',
      storage_device: {},
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
