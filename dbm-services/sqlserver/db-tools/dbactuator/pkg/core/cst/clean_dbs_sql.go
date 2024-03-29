/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cst

var TRUNCATE_TABLES_SQL = `
use [%s]
EXEC sp_MSForEachTable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'
EXEC sp_MSForEachTable 'ALTER TABLE ? DISABLE TRIGGER ALL'
EXEC sp_MSForEachTable 'TRUNCATE TABLE ?;'
EXEC sp_MSForEachTable 'ALTER TABLE ? CHECK CONSTRAINT ALL'
EXEC sp_MSForEachTable 'ALTER TABLE ? ENABLE TRIGGER ALL'
`

var DROP_TABLES_SQL = `
use [%s]
EXEC sp_MSForEachTable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'
EXEC sp_MSForEachTable 'ALTER TABLE ? DISABLE TRIGGER ALL'
EXEC sp_MSForEachTable 'DROP TABLE ?;'
`
var TRUNCATE_TABLES_SQL_FOR_PER = `
use [%s]
ALTER TABLE [%s] NOCHECK CONSTRAINT ALL;
ALTER TABLE [%s] DISABLE TRIGGER ALL;
TRUNCATE TABLE [%s];
ALTER TABLE [%s] CHECK CONSTRAINT ALL;
ALTER TABLE [%s] ENABLE TRIGGER ALL;
`

var DROP_TABLES_SQL_FOR_PER = `
use %s
ALTER TABLE [%s] NOCHECK CONSTRAINT ALL;
ALTER TABLE [%s] DISABLE TRIGGER ALL;
DROP TABLE [%s];
`
