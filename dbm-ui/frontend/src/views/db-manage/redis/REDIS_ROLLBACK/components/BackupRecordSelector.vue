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
    class="backup-record-selector-dialog"
    :is-show="isShow"
    :width="1200"
    @closed="handleClose">
    <template #header>
      <span>
        {{ t('选择备份记录') }}
        <span class="header-domain">{{ cluster.cluster_domain }}</span>
      </span>
    </template>
    <div class="selector-body">
      <!-- 左栏：备份记录列表 -->
      <section class="pane">
        <div class="pane-head">
          <BkDatePicker
            v-model="queryTime"
            append-to-body
            :clearable="false"
            :disabled-date="disableQueryDate"
            :shortcuts="queryTimeShortcuts"
            type="datetimerange" />
        </div>
        <BkLoading
          class="pane-body"
          :loading="isBatchLoading">
          <div class="batch-list">
            <div
              v-for="batchItem in batchList"
              :key="batchItem.backup_identify"
              class="batch-item"
              :class="{
                'is-active': selectedBatch?.backup_identify === batchItem.backup_identify,
              }"
              @click="handleSelectBatch(batchItem)">
              <div class="batch-item-title">{{ batchItem.backup_identify }}</div>
              <div class="batch-item-meta">
                {{ utcToLocal(batchItem.start_time) }} ~ {{ utcToLocal(batchItem.end_time).slice(11) }} ·
                {{ batchItem.backupTypeText }} ·
                {{ t('n 个分片', { n: batchItem.shard_count }) }}
              </div>
              <div
                v-if="getTopoWarning(batchItem)"
                class="batch-item-topo">
                <DbIcon type="gaojing" />
                {{ getTopoWarning(batchItem) }}
              </div>
            </div>
            <EmptyStatus
              v-if="!isBatchLoading && batchList.length === 0"
              class="w-100"
              :is-anomalies="false"
              :is-searching="false"
              @refresh="fetchBatches" />
          </div>
        </BkLoading>
      </section>
      <!-- 右栏：构造设置 -->
      <section class="pane">
        <div class="pane-head">
          <div class="pane-title">{{ selectedBatch?.backup_identify || t('构造设置') }}</div>
          <div class="pane-meta">{{ rightPaneMeta }}</div>
        </div>
        <div class="pane-body is-padded">
          <template v-if="selectedBatch">
            <BkAlert
              v-if="selectedTopoWarning"
              class="mb-12"
              theme="warning"
              :title="selectedTopoWarning" />
            <div class="section">
              <div class="section-label"><span class="req">*</span>{{ t('构造范围') }}</div>
              <BkRadioGroup v-model="scope">
                <BkRadio label="all">
                  {{ t('全部（n 个分片）', { n: selectedBatch.shard_count }) }}
                </BkRadio>
                <BkRadio label="pick">
                  {{ t('指定分片') }}
                </BkRadio>
              </BkRadioGroup>
            </div>
            <template v-if="scope === 'pick'">
              <BkLoading :loading="isShardLoading">
                <DbQuickSearch
                  v-model="searchValue"
                  class="mt-8 mb-8"
                  :data="searchSelectData"
                  @change="handleSearchChange" />
                <div
                  v-if="keyRouteWarning"
                  class="key-route-warning mb-8">
                  {{ keyRouteWarning }}
                </div>
                <PrimaryTable
                  class="shard-table"
                  :data="filteredShards"
                  :max-height="260"
                  row-key="shard_value">
                  <TableColumn
                    col-key="selection"
                    :width="60">
                    <template #title>
                      <BkCheckbox
                        :indeterminate="isFilteredIndeterminate"
                        :model-value="isAllFilteredChecked"
                        @change="handleFilterSelectAll" />
                    </template>
                    <template #default="{ row }: { row: RollbackBatchShard }">
                      <BkCheckbox
                        :model-value="Boolean(checkedShardMap[row.shard_value])"
                        @change="(value: boolean) => handleCheckShard(row.shard_value, value)" />
                    </template>
                  </TableColumn>
                  <TableColumn
                    col-key="shard_value"
                    :min-width="140"
                    :title="t('分片')" />
                  <TableColumn
                    col-key="source_instance"
                    :min-width="160"
                    :title="t('实例')">
                    <template #default="{ row }: { row: RollbackBatchShard }">
                      {{ row.source_ip }}:{{ row.source_port }}
                    </template>
                  </TableColumn>
                  <TableColumn
                    col-key="size"
                    :min-width="120"
                    :title="t('全备大小')">
                    <template #default="{ row }: { row: RollbackBatchShard }">
                      {{ bytePretty(row.size) }}
                    </template>
                  </TableColumn>
                </PrimaryTable>
                <div class="picked-count">
                  {{ t('已选 n / m 个分片', { n: checkedShardValues.length, m: selectedBatch.shard_count }) }}
                </div>
              </BkLoading>
            </template>
          </template>
          <template v-if="selectedBatch && hasBinlogArch">
            <div class="section mt-16">
              <div class="section-label">{{ t('构造到') }}</div>
              <BkDatePicker
                v-model="recoveryTimePoint"
                append-to-body
                :clearable="false"
                :disabled-date="disableRecoveryDate"
                :placeholder="t('留空则仅用全备')"
                type="datetime" />
              <div
                v-if="isRecoveryInvalid"
                class="recovery-error mt-4">
                {{ t('构造到的时间不能早于 n', { n: localLowerBound }) }}
              </div>
              <p class="section-hint mt-4">
                {{
                  t('留空则只用全备恢复；填写后，在全备基础上重放 binlog 追到该时间点，不早于 n。', {
                    n: localLowerBound || t('所选全备的最晚结束时间'),
                  })
                }}
              </p>
              <template v-if="recoveryTimePoint">
                <BkCheckbox
                  v-model="allowBinlog"
                  class="mt-8">
                  <span>{{ t('binlog 不连续仍构造') }}</span>
                </BkCheckbox>
                <p class="section-hint mt-4">
                  {{ t('分片 binlog 不连续时跳过缺失部分继续重放，构造结果可能与原集群数据不一致') }}
                </p>
              </template>
            </div>
          </template>
          <div
            v-if="!selectedBatch"
            class="pane-empty">
            {{ t('请先在左侧选择备份记录') }}
          </div>
        </div>
      </section>
    </div>
    <template #footer>
      <span
        v-bk-tooltips="confirmTooltip"
        class="mr-8">
        <BkButton
          :disabled="isConfirmDisabled"
          theme="primary"
          @click="handleConfirm">
          {{ t('确认选择') }}
        </BkButton>
      </span>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import RollbackBatch from '@services/model/redis/rollback-batch';
  import RollbackBatchShard from '@services/model/redis/rollback-batch-shard';
  import { getRollbackBatchDetails, getRollbackBatches, getShardRoute } from '@services/source/redisRollback';

  import { ipv4 } from '@common/regex';

  import { comType } from '@components/db-quick-search/bk-quick-search/constants';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { bytePretty } from '@utils';

  import { createBackupRecord, getTimeZoneOffset, hasBinlog, type IBackupRecord, utcToLocal } from './backup-record';

  interface Props {
    cluster: {
      cluster_domain: string;
      cluster_type: string;
      id: number;
    };
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const modelValue = defineModel<IBackupRecord | null>({
    default: null,
  });

  const { t } = useI18n();

  // 查询时间快捷项：同页各行共用（组件实例唯一，状态天然共享），默认最近 3 天
  const queryTimeShortcuts = [1, 3, 7, 15].map((days) => ({
    text: t('最近 n 天', { n: days }),
    value: () => [dayjs().subtract(days, 'day').toDate(), new Date()] as [Date, Date],
  }));

  // 输入是否为 IP（正则取自 common/regex）
  const isIpLike = (value: string) => ipv4.test(value);

  // 未选字段直接输入时，SuggestMenu 按各搜索项 validator 生成建议项：形如 IP 只命中 IP，其余只命中 Key；两个字段均支持多选
  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
      type: comType.MULTIPLE_INPUT,
      validator: isIpLike,
    },
    {
      id: 'key',
      name: 'Key',
      type: comType.MULTIPLE_INPUT,
      validator: (value: string) => !isIpLike(value),
    },
  ];

  const isBatchLoading = ref(false);
  const isShardLoading = ref(false);

  // 查询时间窗口：ref 默认最近 3 天；清空后（组件内部会置为 ['','']）接口处回退默认 7 天
  const queryTime = ref<[Date, Date]>([dayjs().subtract(3, 'day').toDate(), new Date()]);

  const getQueryTimeRange = (): [Date, Date] => {
    const [start, end] = queryTime.value;
    if (start && end) {
      return [start, end];
    }
    return [dayjs().subtract(7, 'day').toDate(), new Date()];
  };

  const batchList = ref<RollbackBatch[]>([]);
  const currentShardCount = ref(0);
  const selectedBatch = ref<RollbackBatch | null>(null);

  const scope = ref<'all' | 'pick'>('all');
  const checkedShardValues = ref<string[]>([]);
  const shardList = ref<RollbackBatchShard[]>([]);

  const searchValue = ref<Record<string, string>>({});
  const keyRouteWarning = ref('');

  const recoveryTimePoint = ref('');
  const allowBinlog = ref(false);

  const lastClusterId = ref(0);
  // 标记 programmatic 赋值，避免 watch 误触发请求
  const isRestoring = ref(false);

  const checkedShardMap = computed(() => Object.fromEntries(checkedShardValues.value.map((item) => [item, true])));

  const hasBinlogArch = computed(() => hasBinlog(props.cluster.cluster_type));

  // 拓扑不一致：备份时分片数与当前集群分片数不同
  const getTopoWarning = (batchItem: RollbackBatch) =>
    currentShardCount.value && batchItem.shard_count !== currentShardCount.value
      ? t('备份时 x 个分片，当前 y 个分片，将按备份时的分片构造', {
          x: batchItem.shard_count,
          y: currentShardCount.value,
        })
      : '';

  const selectedTopoWarning = computed(() => (selectedBatch.value ? getTopoWarning(selectedBatch.value) : ''));

  // 右栏标题栏 meta：起止时间（所选时区） · 备份方式
  const rightPaneMeta = computed(() =>
    selectedBatch.value
      ? `${utcToLocal(selectedBatch.value.start_time)} ~ ${utcToLocal(selectedBatch.value.end_time)} · ${selectedBatch.value.backupTypeText}`
      : '',
  );

  // 参与构造分片中最晚的全备结束时间（UTC）
  const lowerBound = computed(() => {
    if (!selectedBatch.value) {
      return '';
    }
    if (scope.value === 'all') {
      return selectedBatch.value.end_time;
    }
    const checkedShards = shardList.value.filter((item) => checkedShardMap.value[item.shard_value]);
    if (checkedShards.length === 0) {
      return '';
    }
    return checkedShards.reduce((max, item) => (item.backup_end_time > max ? item.backup_end_time : max), '');
  });

  // 下限展示：转页面所选时区
  const localLowerBound = computed(() => utcToLocal(lowerBound.value));

  // 构造到（所选时区的本地时间）与下限（UTC）比较：统一转绝对时间
  const isRecoveryInvalid = computed(() => {
    if (!recoveryTimePoint.value || !lowerBound.value) {
      return false;
    }
    const recoveryValue = dayjs(`${recoveryTimePoint.value}${getTimeZoneOffset()}`).valueOf();
    const lowerBoundValue = dayjs.utc(lowerBound.value).valueOf();
    return recoveryValue < lowerBoundValue;
  });

  // Key 筛选命中（shard_route 反查结果）：有 key 筛选时表格只展示命中的分片，无 key 展示全量
  const keyHitShardValues = ref<string[]>([]);

  // 展示范围：key 命中 ∩ IP 命中（各条件存在才参与过滤），ip 同时用于勾选
  const filteredShards = ref<RollbackBatchShard[]>([]);

  // 分片列表或筛选结果变化后需显式调用，同步展示范围
  const updateFilteredShards = () => {
    let result = [...shardList.value];
    if (keyHitShardValues.value.length > 0) {
      const hitMap = Object.fromEntries(keyHitShardValues.value.map((item) => [item, true]));
      result = result.filter((item) => hitMap[item.shard_value]);
    }
    const ipValues = (searchValue.value.ip || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    if (ipValues.length > 0) {
      result = result.filter((item) =>
        ipValues.some((ipCondition) => {
          const ip = ipCondition.split(':')[0]!;
          return item.source_ip.includes(ip) || `${item.source_ip}:${item.source_port}`.includes(ipCondition);
        }),
      );
    }
    filteredShards.value = result;
  };

  const isAllFilteredChecked = computed(
    () =>
      filteredShards.value.length > 0 && filteredShards.value.every((item) => checkedShardMap.value[item.shard_value]),
  );

  const isFilteredIndeterminate = computed(
    () => !isAllFilteredChecked.value && filteredShards.value.some((item) => checkedShardMap.value[item.shard_value]),
  );

  const isConfirmDisabled = computed(() => {
    if (!selectedBatch.value) {
      return true;
    }
    if (scope.value === 'pick' && checkedShardValues.value.length === 0) {
      return true;
    }
    return isRecoveryInvalid.value;
  });

  // 确认按钮 tooltips：仅禁用时提示原因，可用时不显示
  const confirmTooltip = computed(() => {
    if (!selectedBatch.value) {
      return { content: t('请先在左侧选择备份记录'), disabled: false };
    }
    if (isRecoveryInvalid.value) {
      return {
        content: t('构造到的时间不能早于 n', { n: localLowerBound.value }),
        disabled: false,
      };
    }
    if (scope.value === 'pick' && checkedShardValues.value.length === 0) {
      return { content: t('请先勾选参与构造的分片'), disabled: false };
    }
    return { content: '', disabled: true };
  });

  // 查询时间跨度不得超过 30 天（list_batches 接口限制）
  const disableQueryDate = (date: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  // 构造到：禁用未来日期，以及早于参与构造全备最晚结束时间（下限）的日期
  const disableRecoveryDate = (date: Date | number) =>
    dayjs(date).isAfter(dayjs(), 'day') ||
    (Boolean(localLowerBound.value) && dayjs(date).isBefore(dayjs(localLowerBound.value), 'day'));

  const fetchBatches = () => {
    isBatchLoading.value = true;
    const [start, end] = getQueryTimeRange();
    return getRollbackBatches({
      cluster_id: props.cluster.id,
      end_time: `${dayjs(end).format('YYYY-MM-DD HH:mm:ss')}${getTimeZoneOffset()}`,
      start_time: `${dayjs(start).format('YYYY-MM-DD HH:mm:ss')}${getTimeZoneOffset()}`,
    })
      .then((res) => {
        batchList.value = res.batches;
        currentShardCount.value = res.cluster_shards.length;
      })
      .finally(() => {
        isBatchLoading.value = false;
      });
  };

  // 分片请求序号：切换批次/记录时旧请求可能后返回，只让最新一次的结果生效
  let shardRequestSeq = 0;

  const fetchShards = (restoreChecked: string[] = []) => {
    if (!selectedBatch.value) {
      return;
    }
    const seq = ++shardRequestSeq;
    isShardLoading.value = true;
    getRollbackBatchDetails({
      backup_identify: selectedBatch.value.backup_identify,
      cluster_id: props.cluster.id,
    })
      .then((res) => {
        if (seq !== shardRequestSeq) {
          return;
        }
        shardList.value = res.shards;
        checkedShardValues.value = restoreChecked.filter((item) =>
          shardList.value.some((shardItem) => shardItem.shard_value === item),
        );
        updateFilteredShards();
      })
      .finally(() => {
        if (seq === shardRequestSeq) {
          isShardLoading.value = false;
        }
      });
  };

  watch(isShow, (show) => {
    if (!show) {
      return;
    }
    const isClusterChanged = lastClusterId.value !== props.cluster.id;
    if (isClusterChanged) {
      lastClusterId.value = props.cluster.id;
      batchList.value = [];
      selectedBatch.value = null;
      shardList.value = [];
      keyRouteWarning.value = '';
      keyHitShardValues.value = [];
      searchValue.value = {};
      fetchBatches();
    }
    // 回显本行已选记录；未选过则重置为默认态
    isRestoring.value = true;
    const record = modelValue.value;
    if (record) {
      // 清掉上一次会话遗留的过滤条件，避免分片表格被旧条件过滤成空
      searchValue.value = {};
      keyRouteWarning.value = '';
      keyHitShardValues.value = [];
      selectedBatch.value = new RollbackBatch({
        backup_identify: record.backup_identify,
        backup_type: record.backup_type,
        end_time: record.end_time,
        is_all_shards_covered: true,
        is_complete: true,
        shard_count: record.shard_count,
        source_is_all_current: true,
        start_time: record.start_time,
        total_size: 0,
      });
      scope.value = record.scope;
      recoveryTimePoint.value = record.recovery_time_point;
      allowBinlog.value = record.allow_binlog_nonconsecutive;
      // 初始化即拉取分片列表并回显勾选，保证切换到「指定分片」时表格有数据
      fetchShards(record.shard_values);
      // 再次提单回填的 shard_count / 起止时间不可靠，用真实批次数据修正右侧信息
      const syncSelectedBatch = () => {
        const matched = batchList.value.find((item) => item.backup_identify === record.backup_identify);
        if (matched) {
          selectedBatch.value = matched;
          return true;
        }
        return false;
      };
      if (!syncSelectedBatch()) {
        fetchBatches().then(syncSelectedBatch);
      }
    } else {
      selectedBatch.value = null;
      scope.value = 'all';
      checkedShardValues.value = [];
      shardList.value = [];
      recoveryTimePoint.value = '';
      allowBinlog.value = false;
      keyRouteWarning.value = '';
      keyHitShardValues.value = [];
      searchValue.value = {};
    }
    nextTick(() => {
      isRestoring.value = false;
    });
  });

  // 查询时间变化重新拉取批次列表；跨度超过 30 天时截断（list_batches 接口限制）；清空后回退默认 7 天
  watch(queryTime, (value) => {
    if (!isShow.value || isBatchLoading.value) {
      return;
    }
    if (!value) {
      selectedBatch.value = null;
      fetchBatches();
      return;
    }
    const [start, end] = value;
    if (dayjs(end).diff(start, 'day') > 30) {
      queryTime.value = [start, dayjs(start).add(30, 'day').toDate()];
      Message({
        message: t('查询时间跨度不能超过 30 天'),
        theme: 'warning',
      });
      return;
    }
    selectedBatch.value = null;
    fetchBatches();
  });

  const handleSelectBatch = (batchItem: RollbackBatch) => {
    if (selectedBatch.value?.backup_identify === batchItem.backup_identify) {
      return;
    }
    selectedBatch.value = batchItem;
    // 切换备份记录：构造范围回「全部」、构造到清空、binlog 勾选取消
    isRestoring.value = true;
    scope.value = 'all';
    checkedShardValues.value = [];
    shardList.value = [];
    recoveryTimePoint.value = '';
    allowBinlog.value = false;
    keyRouteWarning.value = '';
    keyHitShardValues.value = [];
    searchValue.value = {};
    updateFilteredShards();
    nextTick(() => {
      isRestoring.value = false;
    });
  };

  watch(scope, (newScope) => {
    if (isRestoring.value) {
      return;
    }
    if (newScope === 'pick') {
      // 默认展示全部分片：清掉上一次遗留的 IP/Key 过滤条件（已勾选的分片保留）
      if (shardList.value.length === 0) {
        fetchShards(checkedShardValues.value);
      }
      searchValue.value = {};
      keyRouteWarning.value = '';
      keyHitShardValues.value = [];
      updateFilteredShards();
    }
    if (newScope === 'all') {
      checkedShardValues.value = [];
    }
  });

  // Key 过滤经 shard_route 反查所在分片并自动勾选；IP 过滤为本地匹配。
  // 四种过滤组合：1. 无 ip 无 key 恢复全量并清空勾选；2. 仅 ip 本地过滤；3. 仅 key 反查勾选；4. ip + key 同时生效
  const handleSearchChange = () => {
    const ipValues = (searchValue.value.ip || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    const keys = (searchValue.value.key || '')
      .split(/[,\s;，；]+/)
      .map((item) => item.trim())
      .filter(Boolean);
    // 无过滤条件：展示全量并清空勾选
    if (ipValues.length === 0 && keys.length === 0) {
      keyRouteWarning.value = '';
      keyHitShardValues.value = [];
      checkedShardValues.value = [];
      updateFilteredShards();
      return;
    }
    if (!selectedBatch.value) {
      return;
    }
    // IP：本地匹配命中的分片（参与展示过滤，同时作为勾选）
    const ipMatchedValues = ipValues.length
      ? shardList.value
          .filter((item) =>
            ipValues.some((ipCondition) => {
              const ip = ipCondition.split(':')[0]!;
              return item.source_ip.includes(ip) || `${item.source_ip}:${item.source_port}`.includes(ipCondition);
            }),
          )
          .map((item) => item.shard_value)
      : [];
    if (keys.length === 0) {
      // 仅 IP：按命中分片勾选，展示保持全量
      keyRouteWarning.value = '';
      keyHitShardValues.value = [];
      checkedShardValues.value = [...new Set(ipMatchedValues)];
      updateFilteredShards();
      return;
    }
    // 有 Key：反查命中的分片作为展示范围，勾选 = IP 命中 + Key 命中
    isShardLoading.value = true;
    getShardRoute({
      backup_identify: selectedBatch.value.backup_identify,
      cluster_id: props.cluster.id,
      keys: [...new Set(keys)].slice(0, 500),
    })
      .then((res) => {
        keyHitShardValues.value = [...new Set(res.batch_shard_values)];
        checkedShardValues.value = [...new Set([...ipMatchedValues, ...keyHitShardValues.value])];
        if (res.results.some((item) => !item.is_covered)) {
          keyRouteWarning.value = t('该 Key 所在的部分段在备份批次中存在缺口，已尽可能勾选覆盖分片');
        } else {
          keyRouteWarning.value = '';
        }
        updateFilteredShards();
      })
      .finally(() => {
        isShardLoading.value = false;
      });
  };

  const handleCheckShard = (shardValue: string, checked: boolean) => {
    if (checked) {
      checkedShardValues.value = [...checkedShardValues.value, shardValue];
    } else {
      checkedShardValues.value = checkedShardValues.value.filter((item) => item !== shardValue);
    }
  };

  // 表头全选只作用于当前过滤结果
  const handleFilterSelectAll = (checked: boolean) => {
    const filteredValues = filteredShards.value.map((item) => item.shard_value);
    if (checked) {
      checkedShardValues.value = [...new Set([...checkedShardValues.value, ...filteredValues])];
    } else {
      const filteredMap = Object.fromEntries(filteredValues.map((item) => [item, true]));
      checkedShardValues.value = checkedShardValues.value.filter((item) => !filteredMap[item]);
    }
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = () => {
    if (!selectedBatch.value) {
      return;
    }
    modelValue.value = createBackupRecord({
      allow_binlog_nonconsecutive: recoveryTimePoint.value ? allowBinlog.value : false,
      backup_identify: selectedBatch.value.backup_identify,
      backup_type: selectedBatch.value.backup_type,
      current_shard_count: currentShardCount.value,
      end_time: selectedBatch.value.end_time,
      recovery_time_point: recoveryTimePoint.value ? dayjs(recoveryTimePoint.value).format('YYYY-MM-DD HH:mm:ss') : '',
      scope: scope.value,
      shard_count: selectedBatch.value.shard_count,
      shard_max_backup_end_time: lowerBound.value,
      shard_values: scope.value === 'pick' ? [...checkedShardValues.value] : [],
      start_time: selectedBatch.value.start_time,
    });
    handleClose();
  };
</script>

<style lang="less">
  .backup-record-selector-dialog {
    .header-domain {
      margin-left: 8px;
      font-size: 14px;
      color: #979ba5;
    }

    // 左右两栏布局（420px + 自适应）
    .selector-body {
      display: grid;
      grid-template-columns: 440px minmax(0, 1fr);
      gap: 16px;
    }

    .pane {
      display: flex;
      height: 56vh;
      min-width: 0;
      flex-direction: column;
      border: 1px solid #dcdee5;
      border-radius: 3px;
    }

    .pane-head {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
      padding: 12px;
      border-bottom: 1px solid #eaebf0;

      .pane-title {
        font-size: 14px;
        font-weight: bolder;
        color: #313238;
      }

      .pane-meta {
        font-size: 12px;
        color: #979ba5;
      }
    }

    // BkLoading 的包裹层是普通 div，需让其撑满并成为滚动容器
    .pane-body {
      flex: 1;
      min-height: 0;
      padding: 8px;
      overflow: auto;

      &.is-padded {
        padding: 12px 16px;
      }

      .bk-loading-wrapper,
      .bk-loading {
        min-height: 100%;
      }
    }

    .batch-item {
      padding: 8px 12px;
      margin-bottom: 4px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      border: 1px solid transparent;
      border-radius: 3px;

      &:hover {
        background: #f5f7fa;
      }

      &.is-active {
        background: #e1ecff;
        border-color: #3a84ff;
      }

      .batch-item-title {
        font-size: 14px;
        font-weight: bolder;
        color: #313238;
      }

      .batch-item-meta {
        margin-top: 2px;
        color: #979ba5;
      }

      .batch-item-topo {
        margin-top: 2px;
        color: #eb9000;
      }
    }

    .section-label {
      margin-bottom: 8px;
      font-size: 12px;
      color: #63656e;

      .req {
        margin-right: 4px;
        color: #ea3636;
      }
    }

    .section-hint {
      font-size: 12px;
      color: #979ba5;
    }

    .key-route-warning {
      padding: 4px 8px;
      font-size: 12px;
      color: #ff9c01;
      background: #fff4e2;
    }

    .picked-count {
      margin-top: 8px;
      font-size: 12px;
      // 与 section-hint 同色
      color: #979ba5;
    }

    .recovery-error {
      font-size: 12px;
      color: #ea3636;
    }

    .pane-empty {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #979ba5;
    }
  }
</style>
