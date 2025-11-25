<template>
  <BkFormItem
    :label="t('资源标签')"
    :property="property"
    required
    :rules="rules">
    <div style="display: flex">
      <ResourceTagSelector
        ref="resourceTagSelector"
        v-model="tagList"
        :biz-id="Number(bizId) || undefined"
        :params="params"
        style="width: 435px" />
      <BkButton
        class="ml-8"
        outline
        theme="primary"
        @click="handleClick">
        {{ t('资源预览') }}
      </BkButton>
    </div>
  </BkFormItem>
  <ResourcePreviewSiderslider
    v-model:is-show="showSlider"
    :biz-id="Number(bizId) || undefined"
    :params="params" />
</template>

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import ResourcePreviewSiderslider from '@components/resource-preview-sideslider/Index.vue';

  import ResourceTagSelector from './ResourceTagSelector.vue';

  interface Props {
    bizId?: number | string;
    params: ComponentProps<typeof ResourcePreviewSiderslider>['params'];
    property: string;
  }

  defineProps<Props>();

  const tagList = defineModel<
    {
      id: number;
      value: string;
    }[]
  >('tagList', {
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('请选择资源标签'),
      required: true,
      trigger: 'change',
      validator: () => resourceTagSelector.value?.validate(),
    },
  ];

  const resourceTagSelector = useTemplateRef('resourceTagSelector');

  const showSlider = ref(false);

  const handleClick = () => {
    showSlider.value = true;
  };
</script>
