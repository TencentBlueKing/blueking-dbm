<template>
  <div>
    <BkDialog
      :is-show="isShow"
      render-directive="if"
      :title="computedTitle"
      @closed="handleClose"
      @confirm="handleConfirm">
      <BkForm
        :ref="formInstance"
        form-type="vertical"
        :model="formModel"
        :rules="rules">
        <BkFormItem
          :label="t('标签')"
          required>
          <BkTagInput
            v-model="formModel.tags"
            allow-create
            :clearable="false"></BkTagInput>
        </BkFormItem>
      </BkForm>
    </BkDialog>
  </div>
</template>

<script lang="tsx">
  import { defineComponent, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { createResourceTag, getAllResourceTags } from '@/services/source/tag';

  export type ValidateInfo = {
    res: boolean;
    message: string;
  };

  export default defineComponent({
    props: {
      isShow: Boolean,
      bkBizId: String,
    },
    emits: ['update:isShow'],
    setup(props, { emit }) {
      const { t } = useI18n();

      const existedTagsSet = ref<Set<string>>(new Set());
      const formInstance = ref();
      const submitLoading = ref(false);
      const formModel = reactive({
        tags: [],
      });

      const computedTitle = computed(() => `${t('新建标签')} - ${props.bkBizId}`);
      const rules = computed(() => {
        const { res, message } = handleValidate(formModel.tags);
        return [
          {
            validator: () => res,
            message,
          },
        ];
      });

      watch(
        () => formModel.tags,
        async () => {
          const { results } = await getAllResourceTags();
          existedTagsSet.value = new Set();
          results.map((v) => existedTagsSet.value.add(v));
          await formInstance.value.validate();
        },
      );

      const handleValidate = (arrVal: string[]) => {
        const validateInfo: ValidateInfo = {
          res: true,
          message: '',
        };
        if (!arrVal.length) {
          return Object.assign({}, validateInfo, {
            res: false,
            message: '',
          });
        }
        const existedArr = [];
        for (const item of arrVal) {
          if (existedTagsSet.value.has(item)) {
            existedArr.push(item);
          }
        }
        const validateRes = !existedArr.values.length;
        return Object.assign({}, validateInfo, {
          res: validateRes,
          message: validateRes ? '' : `${existedArr.join(',')}已存在`,
        });
      };

      const handleConfirm = async () => {
        submitLoading.value = true;
        try {
          await createResourceTag(formModel.tags);
          handleClose();
        } finally {
          submitLoading.value = false;
        }
      };

      const handleClose = () => {
        emit('update:isShow', false);
      };

      return {
        computedTitle,
        t,
        formModel,
        formInstance,
        rules,
        handleConfirm,
        handleClose,
      };
    },
  });
</script>

<style scoped></style>
