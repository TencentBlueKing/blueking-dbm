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
  <BkFormItem
    :label="t('版本')"
    property="details.db_version"
    required>
    <DbSelect
      v-model="modelValue"
      class="item-input"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading">
      <DbOption
        v-for="item in versionList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </DbSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAddonVersions } from '@services/source/kubernetesToolbox';

  interface Props {
    addonType: ServiceParameters<typeof getAddonVersions>['addonType'];
    applyMode?: string;
    bkBizId?: number | string;
  }

  const props = withDefaults(defineProps<Props>(), {
    applyMode: 'SharedMode',
    bkBizId: '',
  });
  const modelValue = defineModel<string>({
    required: true,
  });
  const majorVersion = defineModel<string>('majorVersion', {
    required: true,
  });

  const { t } = useI18n();

  // 独占集群（isPublic=false）时按业务 ID 取该业务独占的可用版本
  const isPublic = computed(() => props.applyMode !== 'ExclusiveMode');
  const bkBizId = computed(() => (props.bkBizId ? Number(props.bkBizId) : undefined));

  const versionList = computed(() =>
    (versionData.value || []).flatMap((item) =>
      item.supportedVersions.map((subItem) => ({
        label: `${subItem}`,
        value: subItem,
      })),
    ),
  );

  const versionMap = computed(() =>
    Object.fromEntries(
      (versionData.value || []).flatMap((item) =>
        item.supportedVersions.map((subItem) => [subItem, item.addonVersion]),
      ),
    ),
  );

  const {
    data: versionData,
    loading: isLoading,
    run,
  } = useRequest(getAddonVersions, {
    manual: true,
    onSuccess(data) {
      // 部署类型/业务变化后已选版本可能不在新列表中，清空避免提交失效数据
      if (modelValue.value && !data.some((item) => item.supportedVersions.includes(modelValue.value))) {
        modelValue.value = '';
        majorVersion.value = '';
      }
    },
  });

  watch(
    [() => props.addonType, isPublic, bkBizId],
    () => {
      // 业务 ID 未就绪时不请求，避免回显过程中先按默认业务取一次造成结果竞态
      if (!bkBizId.value) {
        return;
      }
      run({
        addonType: props.addonType,
        bkBizId: bkBizId.value,
        isPublic: isPublic.value,
      });
    },
    { immediate: true },
  );

  watch([modelValue, versionData], () => {
    if (modelValue.value && versionList.value) {
      majorVersion.value = versionMap.value[modelValue.value] || '';
    }
  });
</script>
