/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

// TagOperation 的 getValue 契约；不直接引用组件类型，因其内部 Exposes 接口未导出，跨文件无法命名
interface TagOperationInstance {
  getValue: (isIgnoreVerify?: boolean) => Promise<{ key: string; value: string }[] | null>;
}

/**
 * 单集群部署页的「集群标签」编辑器状态与提交逻辑，
 * 模板接入见 REDIS_CLUSTER_APPLY/Index.vue 的「集群标签」表单项
 */
export const useDeployClusterTags = () => {
  const tagOperationRef = ref<TagOperationInstance>();
  // 变更键强制重建编辑器：TagOperation 在 data 从有到空时不会清空内部已编辑行
  const tagEditorKey = ref(0);
  const tagEditorData = ref<{ id: number; key: string; value: string }[]>([]);

  /** 单据详情回填：单键对象数组转编辑器 key/value 行并重建 */
  const initEditorTags = (tags?: Record<string, string>[]) => {
    tagEditorData.value = (tags ?? []).map((item, index) => ({
      id: index,
      key: Object.keys(item)[0] ?? '',
      value: Object.values(item)[0] ?? '',
    }));
    tagEditorKey.value += 1;
  };

  /** 重置编辑器为默认空白行 */
  const resetEditorTags = () => {
    tagEditorData.value = [];
    tagEditorKey.value += 1;
  };

  /**
   * 取标签提交数据（单键对象数组）；
   * 半填行由 TagOperation 内部 form-item 校验拦截并返回 null，全空行在内部过滤掉
   */
  const getSubmitTags = async () => {
    const rows = await tagOperationRef.value?.getValue(false);
    // validate 失败时 getValue 返回 null，透传 null 阻断提交
    if (rows === null) {
      return null;
    }
    return (rows ?? []).map(({ key, value }) => ({ [key]: value }));
  };

  return {
    getSubmitTags,
    initEditorTags,
    resetEditorTags,
    tagEditorData,
    tagEditorKey,
    tagOperationRef,
  };
};
