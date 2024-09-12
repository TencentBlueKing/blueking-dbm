<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkDialog
    class="instance-selector-main"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    width="80%"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      collapsible
      initial-divide="320px"
      :max="360"
      :min="320"
      placement="right">
      <template #main>
        <div class="head-box">
          <div class="selector-title">{{ t('资源池手动选择') }}</div>
          <BkAlert
            class="mb-8"
            closable
            theme="info"
            title="已自定义过滤出符合要求的可用机器" />
        </div>
        <Table
          :disable-host-method="disableHostMethod"
          :last-values="lastValues"
          @change="handleChange">
        </Table>
      </template>
      <template #aside>
        <PreviewResult
          :last-values="lastValues"
          @change="handleChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span class="mr24">
        <slot
          :host-list="lastValues || []"
          name="submitTips" />
      </span>
      <span
        v-bk-tooltips="submitButtonDisabledInfo.tooltips"
        class="inline-block">
        <BkButton
          class="w-88"
          :disabled="submitButtonDisabledInfo.disabled"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8 w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import PreviewResult from './components/preview-result/Index.vue';
  import Table from './components/table/Index.vue';

  interface Props {
    selected?: DbResourceModel[];
    disableHostMethod?: (data: DbResourceModel, list: DbResourceModel[]) => boolean | string;
    // eslint-disable-next-line vue/require-default-prop
    disableDialogSubmitMethod?: (list: DbResourceModel[]) => boolean | string;
  }

  interface Emits {
    (e: 'change', value: DbResourceModel[]): void;
  }

  interface Slots {
    submitTips(value: { hostList: DbResourceModel[] }): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    selected: undefined,
    disableHostMethod: () => false,
  });

  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  defineSlots<Slots>();

  const { t } = useI18n();

  const lastValues = ref<DbResourceModel[]>([]);

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    if (props.disableDialogSubmitMethod) {
      const checkValue = props.disableDialogSubmitMethod(lastValues.value);
      if (checkValue) {
        info.disabled = true;
        info.tooltips.disabled = false;
        info.tooltips.content = _.isString(checkValue) ? checkValue : t('无法保存');
      }
    } else if (Object.values(lastValues.value).length === 0) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = t('请选择主机');
    }

    return info;
  });

  watch(isShow, () => {
    if (isShow.value && props.selected) {
      Object.assign(lastValues, props.selected);
    }
  });

  const handleChange = (values: DbResourceModel[]) => {
    lastValues.value = values;
  };

  const handleSubmit = () => {
    emits('change', lastValues.value);
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .instance-selector-main {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .head-box {
      padding: 0 26px 0 16px;

      .selector-title {
        font-size: 16px;
        line-height: 24px;
        padding: 16px 8px;
        color: #313238;
      }
    }

    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }
  }
</style>
