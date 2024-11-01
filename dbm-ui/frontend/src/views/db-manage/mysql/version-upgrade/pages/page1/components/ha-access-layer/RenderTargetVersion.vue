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
  <BkLoading :loading="loading">
    <TableEditSelect
      ref="selectRef"
      v-model="localValue"
      :disabled="!data.clusterData"
      :list="versionList"
      :rules="rules">
      <template #default="{ optionItem, index }">
        <div class="target-version-select-option">
          <div
            v-overflow-tips
            class="option-name">
            {{ optionItem.label }}
          </div>
          <BkTag
            v-if="index === 0"
            class="ml-4"
            size="small"
            theme="info">
            {{ t('推荐') }}
          </BkTag>
        </div>
      </template>
    </TableEditSelect>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getPackages } from '@services/source/package';

  import { versionRegex } from '@common/regex';

  import TableEditSelect, { type IListItem } from '@components/render-table/columns/select/index.vue';

  import { compareVersions } from '@utils';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data: IDataRow;
  }

  interface Exposes {
    getValue: () => Promise<Record<'pkg_id', string>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const selectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref('');
  const versionList = ref<IListItem[]>([]);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标版本不能为空'),
    },
  ];

  const { loading, run: fetchClusterVersions } = useRequest(getPackages, {
    manual: true,
    onSuccess(versions) {
      const currentVersion = props.data.clusterData!.currentVersion.match(versionRegex)![0];
      versionList.value = versions.results.reduce((prevList, versionItem) => {
        const version = versionItem.name.match(versionRegex);
        if (version && compareVersions(version[0], currentVersion) === 1) {
          prevList.push({
            value: versionItem.id,
            label: versionItem.name,
          });
          return prevList;
        }
        return prevList;
      }, [] as IListItem[]);

      if (versionList.value.length) {
        localValue.value = versionList.value[0].value as string;
      }
    },
  });

  watch(
    () => props.data.clusterData?.clusterId,
    (value) => {
      if (value) {
        fetchClusterVersions({
          pkg_type: 'mysql-proxy',
          db_type: 'mysql',
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.data.targetVersion,
    () => {
      localValue.value = props.data.targetVersion || '';
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value!.getValue().then(() => ({ pkg_id: localValue.value }));
    },
  });
</script>

<style lang="less">
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
<style lang="less" scoped>
  .render-text-box {
    position: relative;
    width: 100%;
    min-height: 42px;
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }
</style>
