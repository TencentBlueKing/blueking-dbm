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
  <EditableColumn
    field="target_version.target_package"
    :label="t('目标版本')"
    :loading="loading"
    :min-width="200"
    required>
    <EditableSelect
      v-model="modelValue.pkg_id"
      :list="versionList"
      @change="handleChange">
      <template #option="{ item }">
        <div class="target-version-select-option">
          <div
            v-overflow-tips
            class="option-name">
            {{ item.label }}
          </div>
          <BkTag
            v-if="item.value === suggestVersion"
            class="ml-4"
            size="small"
            theme="info">
            {{ t('推荐') }}
          </BkTag>
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getPackages } from '@services/source/package';

  import { versionRegex } from '@common/regex';

  import { compareVersions } from '@utils';

  interface Props {
    rowData: {
      cluster: {
        id: number;
      };
      current_version: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    pkg_id: number;
    target_package: string;
  }>({
    default: () => ({
      pkg_id: 0,
      target_package: '',
    }),
  });

  const { t } = useI18n();

  const suggestVersion = ref(0);
  const versionList = ref<
    {
      label: string;
      value: number;
    }[]
  >([]);

  const { loading, run: fetchClusterVersions } = useRequest(getPackages, {
    manual: true,
    onSuccess(versions) {
      const currentVersion = props.rowData.current_version?.match(versionRegex)![0] || '';
      versionList.value = versions.results
        .reduce(
          (prevList, versionItem) => {
            const version = versionItem.name.match(versionRegex);
            if (version && compareVersions(version[0], currentVersion) === 1) {
              prevList.push({
                label: versionItem.name,
                value: versionItem.id,
              });
              return prevList;
            }
            return prevList;
          },
          [] as {
            label: string;
            value: number;
          }[],
        )
        .sort((a, b) => {
          return compareVersions(b.label, a.label);
        });

      if (versionList.value.length) {
        const [lastestVersion] = versionList.value;
        suggestVersion.value = lastestVersion.value;
        modelValue.value = {
          pkg_id: lastestVersion.value,
          target_package: lastestVersion.label,
        };
      }
    },
  });

  watch(
    () => props.rowData.cluster.id,
    (value) => {
      if (value) {
        fetchClusterVersions({
          db_type: 'mysql',
          pkg_type: 'mysql-proxy',
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: number) => {
    modelValue.value.target_package = versionList.value.filter((item) => item.value === value)[0].label;
  };
</script>
<style lang="less" scoped>
  .target-version-select-option {
    display: flex;
    align-items: center;

    .option-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
