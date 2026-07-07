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

import { Alert as BkAlert, InfoBox } from 'bkui-vue';
import { useI18n } from 'vue-i18n';

import { deleteComponent, restartComponent } from '@services/source/kubernetesToolbox';

export const useK8sInstanceOperations = (options: { onSuccess: () => void }) => {
  const { t } = useI18n();

  const handleSuccess = () => {
    options.onSuccess();
  };

  const handleDeleteInstance = (params: ServiceParameters<typeof deleteComponent>, node: string) => {
    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      content: () => (
        <>
          <div style='background-color: #F5F7FA; padding: 8px 16px;'>
            <div>
              {t('实例')} :
              <span
                class='ml-8'
                style='color: #313238; font-size: 12px'>
                {params.podName}（{node}）
              </span>
            </div>
          </div>
          <BkAlert
            class='mt-12'
            theme='warning'
            title={t('注意：删除完成后，将按副本配置自动生成新的实例')}
          />
        </>
      ),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: () => {
        deleteComponent(params).then(() => {
          handleSuccess();
        });
      },
      title: t('确定禁删除该实例？'),
      width: 400,
    });
  };

  const handleRestartInstance = (params: ServiceParameters<typeof restartComponent>, role: string, count: number) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定重启'),
      content: () => (
        <>
          <div style='background-color: #F5F7FA; padding: 8px 16px;'>
            {t('将对 surreal 组件下的 n 个实例执行滚动重启，期间服务可能短暂受影响。', { n: count })}
          </div>
          <BkAlert
            class='mt-12'
            theme='warning'
            title={t('注意：滚动重启将逐一重启各节点，整个过程中集群保持可用，但可能出现短暂的查询延迟增加。')}
          />
        </>
      ),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: () => {
        restartComponent(params).then(() => {
          handleSuccess();
        });
      },
      title: t('确定禁重启 n 个 role 实例？', { n: count, role }),
      width: 400,
    });
  };
  return {
    handleDeleteInstance,
    handleRestartInstance,
  };
};
