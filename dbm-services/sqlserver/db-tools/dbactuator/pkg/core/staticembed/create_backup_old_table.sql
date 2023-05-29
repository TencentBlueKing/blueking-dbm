/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[BACKUP_SETTING_OLD]') AND type in (N'U'))
DROP TABLE [dbo].[BACKUP_SETTING_OLD]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BACKUP_SETTING_OLD](
	[FULL_BACKUP_PATH] [varchar](100) NOT NULL,
	[LOG_BACKUP_PATH] [varchar](100) NOT NULL,
	[KEEP_FULL_BACKUP_DAYS] [int] NOT NULL,
	[KEEP_LOG_BACKUP_DAYS] [int] NOT NULL,
) ON [PRIMARY]
GO
