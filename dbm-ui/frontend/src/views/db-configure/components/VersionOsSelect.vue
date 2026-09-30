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
  <DbSelect
    :all-option-id="allOptionId"
    :all-option-text="t('Linux 全部')"
    :clearable="mode === 'specify'"
    :disabled="selectDisabled"
    :filterable="mode === 'specify'"
    :loading="loading"
    :model-value="displayValue"
    multiple
    multiple-mode="tag"
    :placeholder="placeholder"
    @change="handleChange">
    <DbOption
      v-for="os in options"
      :key="os"
      :label="os"
      :value="os" />
  </DbSelect>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { listSupportSystems } from '@services/source/package';
  import { getDbVersionPermitOs } from '@services/source/version';

  import { t } from '@locales/index';

  interface Props {
    mode: 'follow' | 'specify';
    versionId: number | '';
  }

  const props = defineProps<Props>();

  const emit = defineEmits<Emits>();
  const modelValue = defineModel<string[]>({
    default: () => [],
  });
  type Emits = (e: 'change', value: string[]) => void;
  // “全部”仅用于跟随版本包且 Linux 范围不限时的只读回显。
  const allOptionId = '__linux_all__';
  const osGroups = ref<ServiceReturnType<typeof getDbVersionPermitOs>>([]);
  const supportSystems = ref<string[]>([]);
  const loadFailed = ref(false);
  let requestId = 0;

  const linuxGroup = computed(() => osGroups.value.find((item) => item.permit_os_type === 'Linux'));
  const options = computed(() => {
    if (!linuxGroup.value) return [];
    return [...new Set(linuxGroup.value.permit_os.length ? linuxGroup.value.permit_os : supportSystems.value)];
  });

  const displayValue = computed(() => {
    if (props.mode === 'follow') {
      if (!linuxGroup.value) return [];
      return linuxGroup.value.permit_os.length ? linuxGroup.value.permit_os : [allOptionId];
    }
    return modelValue.value;
  });

  const {
    cancel,
    loading,
    run: fetchOs,
  } = useRequest(
    async (params: { mode: Props['mode']; requestId: number; versionId: number }) => {
      const groups = await getDbVersionPermitOs({ db_version_id: params.versionId });
      const group = groups.find((item) => item.permit_os_type === 'Linux');
      // 只有版本的 Linux 范围不限时，指定范围才使用上传介质包的候选列表。
      const systems =
        params.mode === 'specify' && group && group.permit_os.length === 0
          ? ((await listSupportSystems()).Linux ?? [])
          : [];
      return { groups, systems };
    },
    {
      manual: true,
      onError(_error, [params]) {
        if (params.requestId === requestId) loadFailed.value = true;
      },
      onSuccess(data, [params]) {
        if (params.requestId !== requestId) return;
        osGroups.value = data.groups;
        supportSystems.value = data.systems;
        // 已保存的指定范围不因候选刷新而静默删减或扩展。
      },
    },
  );

  const placeholder = computed(() => {
    if (loading.value) return t('加载中');
    if (loadFailed.value) return t('操作系统候选加载失败，请重新选择版本');
    if (osGroups.value.length === 0) return t('该版本暂无可用介质包');
    if (!linuxGroup.value) return t('该版本没有 Linux 类型的已启用介质包');
    return props.mode === 'follow' ? t('跟随版本包') : t('请选择操作系统版本');
  });
  const selectDisabled = computed(
    () => props.mode === 'follow' || loading.value || loadFailed.value || options.value.length === 0,
  );

  watch(
    [() => props.versionId, () => props.mode],
    ([versionId, mode]) => {
      cancel();
      requestId += 1;
      osGroups.value = [];
      supportSystems.value = [];
      loadFailed.value = false;
      if (versionId) fetchOs({ mode, requestId, versionId });
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    requestId += 1;
    cancel();
  });

  const handleChange = (value: string[]) => {
    if (selectDisabled.value) return;
    const next = [...new Set(value)];
    modelValue.value = next;
    emit('change', next);
  };
</script>
