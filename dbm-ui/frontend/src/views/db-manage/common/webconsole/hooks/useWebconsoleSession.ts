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

import { getProfile } from '@services/source/profile';
import {
  createWebconsoleConnection,
  WebconsoleError,
  type WebconsoleOptions,
  type WebconsoleState,
} from '@services/source/webconsoleWs';

import { useSystemEnviron } from '@stores';

import { t } from '@locales/index';

export interface ConsoleCommandResult {
  error_msg?: string;
  query: unknown;
  rows_affected?: number;
}

export interface WebconsoleTab extends WebconsoleOptions {
  busy: boolean;
  error: string;
  execute: (command: string) => Promise<ConsoleCommandResult>;
  key: number;
  mode: 'http' | 'ws';
  setBusy: (busy: boolean) => void;
  state: WebconsoleState;
  timezone: string;
}

export function useWebconsoleSession() {
  const tabs = reactive<Record<number, WebconsoleTab>>({});
  const connections = new Map<number, ReturnType<typeof createWebconsoleConnection>>();
  const generations = new Map<number, object>();
  let tabKey = 0;

  const closeSession = (clusterId: number) => {
    generations.delete(clusterId);
    connections.get(clusterId)?.close();
    connections.delete(clusterId);
    const tab = tabs[clusterId];
    if (tab) {
      tab.state = 'closed';
      tab.error = '';
    }
  };

  const connect = (clusterId: number) => {
    const tab = tabs[clusterId];
    if (!tab || tab.mode !== 'ws' || tab.busy) {
      return;
    }
    closeSession(clusterId);
    const generation = {};
    generations.set(clusterId, generation);
    tab.state = 'connecting';
    const connection = createWebconsoleConnection(
      {
        baseUrl: import.meta.env.DEV ? window.location.origin : useSystemEnviron().urls.BK_DBM_URL,
        clusterId,
        options: { charset: tab.charset, role: tab.role },
      },
      (state, error) => {
        if (generations.get(clusterId) !== generation || tabs[clusterId] !== tab) {
          return;
        }
        tab.state = state;
        tab.error = error && !error.cancelled ? error.message : '';
        if (error && [401, 4401].includes(Number(error.code))) {
          // 用既有只读接口触发 HTTP 登录处理，不猜测登录地址或重放 SQL。
          void getProfile().catch(() => undefined);
        }
      },
    );
    connections.set(clusterId, connection);
    // 初始化失败已落到 tab 状态；不重复弹出提示，也不自动重连。
    void connection.ready.catch(() => undefined);
  };

  const ensureTab = (clusterId: number, role: WebconsoleOptions['role']) => {
    if (!tabs[clusterId]) {
      const key = ++tabKey;
      tabs[clusterId] = {
        busy: false,
        charset: 'default',
        error: '',
        execute: async (command) => {
          const tab = tabs[clusterId];
          const connection = connections.get(clusterId);
          const generation = generations.get(clusterId);
          if (!tab || tab.key !== key || tab.mode !== 'ws' || tab.state !== 'ready' || !connection) {
            throw new WebconsoleError(t('WebConsole_请先连接'));
          }
          const response = await connection.execute(command);
          if (generations.get(clusterId) !== generation || tabs[clusterId] !== tab) {
            throw new WebconsoleError(t('WebConsole_会话已关闭'), undefined, true);
          }
          return {
            error_msg: response.error,
            query: response.result,
            rows_affected: response.rows_affected,
          };
        },
        key,
        mode: 'http',
        role,
        setBusy: (busy) => {
          if (tabs[clusterId]?.key === key) {
            tabs[clusterId].busy = busy;
          }
        },
        state: 'closed',
        timezone: '+08:00',
      };
    }
    return tabs[clusterId];
  };

  const setMode = (clusterId: number, mode: WebconsoleTab['mode']) => {
    const tab = tabs[clusterId];
    if (!tab || tab.busy || tab.mode === mode) {
      return;
    }
    closeSession(clusterId);
    tab.mode = mode;
    if (mode === 'ws') {
      connect(clusterId);
    }
  };

  const removeTab = (clusterId: number) => {
    closeSession(clusterId);
    delete tabs[clusterId];
  };

  const dispose = () => {
    Array.from(connections.keys()).forEach(closeSession);
  };

  onBeforeRouteLeave(() => {
    dispose();
  });
  onMounted(() => {
    window.addEventListener('pagehide', dispose);
  });
  onBeforeUnmount(() => {
    window.removeEventListener('pagehide', dispose);
    dispose();
  });

  return { connect, ensureTab, removeTab, setMode, tabs };
}
