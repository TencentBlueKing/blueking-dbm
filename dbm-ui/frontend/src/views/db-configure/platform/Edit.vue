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
  <div class="configure-edit-container">
    <div class="top-steps">
      <BkSteps
        v-model:cur-step="curStep"
        :before-change="handleStepBeforeChange"
        :controllable="isChange"
        :steps="steps"
        theme="primary" />
    </div>
    <div class="main">
      <BaseInfo
        v-show="curStep === 1"
        ref="contentRef"
        @change="handleChangeValue" />
      <DiffCompare
        v-show="curStep === 2"
        :data="diffData.data.conf_items"
        :origin="diffData.origin" />
    </div>
    <div class="absolute-footer">
      <BkButton
        :disabled="loading || !isChange"
        :theme="buttonInfo.theme"
        @click="handleChangeStep">
        {{ buttonInfo.text }}
      </BkButton>
      <template v-if="!buttonInfo.isNext">
        <BkButton
          :loading="loading"
          theme="primary"
          @click="handlePublish">
          {{ $t('保存并发布') }}
        </BkButton>
      </template>
      <BkButton
        :disabled="loading"
        @click="handleCancel">
        {{ $t('取消') }}
      </BkButton>
    </div>
  </div>
  <BkDialog
    v-model:is-show="publishDialog.isShow"
    class="db-info-dialog"
    dialog-type="show"
    :esc-close="false"
    header-align="center"
    height="auto"
    :quick-close="false"
    theme="primary"
    :title="$t('确认发布')"
    :width="540">
    <BkForm
      ref="publishFormRef"
      class="db-info-dialog__content"
      form-type="vertical"
      :model="publishDialog">
      <p class="mb-16">
        {{ $t('发布后_所有业务下的新增的实例将会引用当前最新配置') }}
      </p>
      <BkFormItem
        :label="$t('备注')"
        property="publish_description"
        required>
        <BkInput
          v-model="publishDialog.publish_description"
          :maxlength="100"
          :placeholder="$t('备注信息有助于你回溯')"
          show-word-limit
          type="textarea" />
      </BkFormItem>
    </BkForm>
    <div class="db-info-dialog__footer">
      <BkButton
        class="mr-8"
        :loading="loading"
        theme="primary"
        @click="handleSaveAndPublish">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        :disabled="loading"
        @click="handleCancelPublish">
        {{ $t('取消') }}
      </BkButton>
    </div>
  </BkDialog>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { updatePlatformConfig } from '@services/configs';
  import type { ConfigBaseDetails, ParameterConfigItem } from '@services/types/configs';

  import DiffCompare from '../components/DiffCompare.vue';
  import BaseInfo from '../components/EditBase.vue';
  import {
    type DiffItem,
    useDiff,
  } from '../hooks/useDiff';

  interface Props {
    clusterType: string,
    confType: string,
    version: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const loading = ref(false);
  const diffData = reactive({
    origin: [] as ParameterConfigItem[],
    data: {} as ConfigBaseDetails,
  });

  // 判断表单内容是否变更
  const isChange = ref(false);
  const handleChangeValue = ({ changed }: { changed: boolean }) => {
    // window.changeConfirm 会在 setTimeout 后变更
    setTimeout(() => {
      isChange.value = changed;
      window.changeConfirm = changed;
    });
  };

  /**
   * 发布配置
   */
  const publishDialog = reactive({
    isShow: false,
    loading: false,
    publish_description: '',
  });
  const handlePublish = () => {
    publishDialog.isShow = true;
  };
  const handleCancelPublish = () => {
    publishDialog.isShow = false;
    publishDialog.publish_description = '';
  };

  /**
   * step info
   */
  const steps = [{
    title: t('基本信息'),
    icon: '1',
  }, {
    title: t('差异对比'),
    icon: '2',
  }];
  const curStep = ref(1);

  /**
   * (pre | next) control
   */
  const buttonInfo = computed<{
    text: string;
    theme: 'success' | 'warning' | 'danger' | 'primary' | undefined;
    isNext: boolean;
  }
  >(() => {
    const isNext = curStep.value === 1;
    return {
      text: isNext ? t('下一步') : t('上一步'),
      theme: isNext ? 'primary' : undefined,
      isNext,
    };
  });
  const contentRef = ref();
  const validate = async () => {
    if (contentRef.value.validate) {
      const validate = await contentRef.value.validate();
      if (!validate) {
        Message({
          message: t('请完善参数值配置'),
          theme: 'error',
        });
        return false;
      }
    }
    return true;
  };
  const handleStepBeforeChange = () => validate();
  const handleChangeStep = async () => {
    if (buttonInfo.value.isNext) {
      const isPass = await validate();
      if (!isPass) return;

      // 获取 diff 数据
      if (contentRef.value.getData) {
        const { origin, data } = contentRef.value.getData();
        diffData.origin = origin;
        diffData.data = data;
      }
    }

    if (buttonInfo.value.isNext) {
      curStep.value += 1;
    } else {
      curStep.value -= 1;
    }
  };

  /**
   * 保存并提交
   */
  const publishFormRef = ref();
  const handleSaveAndPublish = async () => {
    const validate = await publishFormRef.value.validate()
      .then(() => true)
      .catch(() => false);
    if (validate === false) return;

    // 获取 conf_items
    const { data } = useDiff(diffData.data.conf_items, diffData.origin);
    const confItems = data.map((item: DiffItem) => {
      const type = item.status === 'delete' ? 'remove' : 'update';
      const data = item.status === 'delete' ?  item.before : item.after;
      return Object.assign(data, { op_type: type });
    });

    const params = {
      meta_cluster_type: props.clusterType,
      conf_type: props.confType,
      version: props.version,
      conf_items: confItems,
      name: diffData.data.name,
      description: diffData.data.description,
      publish_description: publishDialog.publish_description,
      confirm: 0,
    };
    loading.value = true;
    updatePlatformConfig(params)
      .then(() => {
        window.changeConfirm = false;
        Message({
          message: t('保存并发布成功'),
          theme: 'success',
        });
        handleCancel();
      })
      .finally(() => {
        loading.value = false;
      });
  };

  const handleCancel = () => {
    const { back } = window.history.state;
    if (back) {
      router.go(-1);
    } else {
      const params = {
        name: 'PlatformDbConfigureList',
        params: { ...route.params },
      };
      router.replace(params);
    }
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .configure-edit-container {
    padding: 54px 0;
  }
</style>
