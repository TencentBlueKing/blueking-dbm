/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package migrator

// publishedSchemaSteps returns every step that has already been released.
// The catalog is split into parts only to keep this file readable.
func publishedSchemaSteps() []schemaStep {
	return concatPublishedSteps(
		publishedSchemaStepsPart01(),
		publishedSchemaStepsPart02(),
		publishedSchemaStepsPart03(),
		publishedSchemaStepsPart04(),
		publishedSchemaStepsPart05(),
		publishedSchemaStepsPart06(),
		publishedSchemaStepsPart07(),
		publishedSchemaStepsPart08(),
		publishedSchemaStepsPart09(),
		publishedSchemaStepsPart10(),
		publishedSchemaStepsPart11(),
		publishedSchemaStepsPart12(),
		publishedSchemaStepsPart13(),
		publishedSchemaStepsPart14(),
		publishedSchemaStepsPart15(),
		publishedSchemaStepsPart16(),
		publishedSchemaStepsPart17(),
		publishedSchemaStepsPart18(),
		publishedSchemaStepsPart19(),
		publishedSchemaStepsPart20(),
		publishedSchemaStepsPart21(),
		publishedSchemaStepsPart22(),
		publishedSchemaStepsPart23(),
		publishedSchemaStepsPart24(),
		publishedSchemaStepsPart25(),
		publishedSchemaStepsPart26(),
		publishedSchemaStepsPart27(),
	)
}

// concatPublishedSteps joins the published step parts into one catalog.
func concatPublishedSteps(parts ...[]schemaStep) []schemaStep {
	var steps []schemaStep
	for _, part := range parts {
		steps = append(steps, part...)
	}

	return steps
}

func publishedSchemaStepsPart01() []schemaStep {
	return []schemaStep{
		{
			Version: 1,
			Name:    "000001_create_t_dbha_status",
			Table:   "t_dbha_status",
			Kind:    objectTable,
			Apply: "CREATE TABLE `t_dbha_status` (`machine_id` varchar(128) NOT NULL,`bk_clo" +
				"ud_id` bigint NOT NULL,`db_ip` varchar(128) NOT NULL,`db_port` bigint NO" +
				"T NULL,`harvest_type` varchar(32) NOT NULL DEFAULT 'default',`sequence_i" +
				"d` bigint unsigned NULL,`agent_id` varchar(128) NULL,`ips` json NULL,`me" +
				"ssage_id` varchar(128) NULL,`service_id` varchar(128) NULL,`db_type_name" +
				"` varchar(128) NULL,`access_layer` varchar(128) NULL,`cluster_type` varc" +
				"har(128) NULL,`machine_type` varchar(128) NULL,`instance_role` varchar(1" +
				"28) NULL,`report_timestamp` bigint unsigned NULL,`host` json NULL,`probe" +
				"` json NULL,`event` json NULL,`data` json NULL,`created_at` datetime NUL" +
				"L,`updated_at` datetime NULL,`deleted_at` datetime NULL,PRIMARY KEY (`ma" +
				"chine_id`, `bk_cloud_id`, `db_ip`, `db_port`, `harvest_type`)) ENGINE=In" +
				"noDB DEFAULT CHARSET=utf8mb4",
		},
		{
			Version: 2,
			Name:    "000002_t_dbha_status_machine_id",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "machine_id",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `machine_id` varchar(128) NULL",
		},
		{
			Version: 3,
			Name:    "000003_t_dbha_status_bk_cloud_id",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "bk_cloud_id",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `bk_cloud_id` bigint NULL",
		},
		{
			Version: 4,
			Name:    "000004_t_dbha_status_db_ip",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "db_ip",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `db_ip` varchar(128) NULL",
		},
		{
			Version: 5,
			Name:    "000005_t_dbha_status_db_port",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "db_port",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `db_port` bigint NULL",
		},
		{
			Version: 6,
			Name:    "000006_t_dbha_status_harvest_type",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "harvest_type",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `harvest_type` varchar(32) NOT NULL DEFAULT 'default'",
		},
		{
			Version: 7,
			Name:    "000007_t_dbha_status_sequence_id",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "sequence_id",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `sequence_id` bigint unsigned NULL",
		},
		{
			Version: 8,
			Name:    "000008_t_dbha_status_agent_id",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "agent_id",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `agent_id` varchar(128) NULL",
		},
	}
}

func publishedSchemaStepsPart02() []schemaStep {
	return []schemaStep{
		{
			Version: 9,
			Name:    "000009_t_dbha_status_ips",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "ips",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `ips` json NULL",
		},
		{
			Version: 10,
			Name:    "000010_t_dbha_status_message_id",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "message_id",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `message_id` varchar(128) NULL",
		},
		{
			Version: 11,
			Name:    "000011_t_dbha_status_service_id",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "service_id",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `service_id` varchar(128) NULL",
		},
		{
			Version: 12,
			Name:    "000012_t_dbha_status_db_type_name",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "db_type_name",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `db_type_name` varchar(128) NULL",
		},
		{
			Version: 13,
			Name:    "000013_t_dbha_status_access_layer",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "access_layer",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `access_layer` varchar(128) NULL",
		},
		{
			Version: 14,
			Name:    "000014_t_dbha_status_cluster_type",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "cluster_type",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `cluster_type` varchar(128) NULL",
		},
		{
			Version: 15,
			Name:    "000015_t_dbha_status_machine_type",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "machine_type",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `machine_type` varchar(128) NULL",
		},
		{
			Version: 16,
			Name:    "000016_t_dbha_status_instance_role",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "instance_role",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `instance_role` varchar(128) NULL",
		},
		{
			Version: 17,
			Name:    "000017_t_dbha_status_report_timestamp",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "report_timestamp",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `report_timestamp` bigint unsigned NULL",
		},
	}
}

func publishedSchemaStepsPart03() []schemaStep {
	return []schemaStep{
		{
			Version: 18,
			Name:    "000018_t_dbha_status_host",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "host",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `host` json NULL",
		},
		{
			Version: 19,
			Name:    "000019_t_dbha_status_probe",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "probe",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `probe` json NULL",
		},
		{
			Version: 20,
			Name:    "000020_t_dbha_status_event",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "event",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `event` json NULL",
		},
		{
			Version: 21,
			Name:    "000021_t_dbha_status_data",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "data",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `data` json NULL",
		},
		{
			Version: 22,
			Name:    "000022_t_dbha_status_created_at",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "created_at",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `created_at` datetime NULL",
		},
		{
			Version: 23,
			Name:    "000023_t_dbha_status_updated_at",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "updated_at",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `updated_at` datetime NULL",
		},
		{
			Version: 24,
			Name:    "000024_t_dbha_status_deleted_at",
			Table:   "t_dbha_status",
			Kind:    objectColumn,
			Column:  "deleted_at",
			Apply:   "ALTER TABLE `t_dbha_status` ADD COLUMN `deleted_at` datetime NULL",
		},
		{
			Version: 25,
			Name:    "000025_create_t_dbm_metadata",
			Table:   "t_dbm_metadata",
			Kind:    objectTable,
			Apply: "CREATE TABLE `t_dbm_metadata` (`bk_cloud_id` bigint NOT NULL,`ip` varcha" +
				"r(128) NOT NULL,`port` bigint NOT NULL,`admin_port` bigint NULL,`bk_idc_" +
				"city_id` bigint NULL,`bk_biz_id` bigint NULL,`logical_city_id` bigint NU" +
				"LL,`logcial_city_name` varchar(128) NULL,`cluster` varchar(128) NULL,`cl" +
				"uster_id` bigint NULL,`cluster_type` varchar(128) NULL,`machine_type` va" +
				"rchar(128) NULL,`access_layer` varchar(128) NULL,`status` varchar(128) N" +
				"ULL,`instance_role` varchar(128) NULL,`receiver` mediumtext NULL,`bind_e" +
				"ntry` mediumtext NULL,`proxy_insts` mediumtext NULL,`binlog_dumpers` med" +
				"iumtext NULL,`created_at` datetime NULL,`updated_at` datetime NULL,`dele" +
				"ted_at` datetime NULL,`sync_duration` bigint NULL,PRIMARY KEY (`bk_cloud" +
				"_id`, `ip`, `port`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
		},
	}
}

func publishedSchemaStepsPart04() []schemaStep {
	return []schemaStep{
		{
			Version: 26,
			Name:    "000026_t_dbm_metadata_bk_cloud_id",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "bk_cloud_id",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `bk_cloud_id` bigint NULL",
		},
		{
			Version: 27,
			Name:    "000027_t_dbm_metadata_ip",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "ip",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `ip` varchar(128) NULL",
		},
		{
			Version: 28,
			Name:    "000028_t_dbm_metadata_port",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "port",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `port` bigint NULL",
		},
		{
			Version: 29,
			Name:    "000029_t_dbm_metadata_admin_port",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "admin_port",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `admin_port` bigint NULL",
		},
		{
			Version: 30,
			Name:    "000030_t_dbm_metadata_bk_idc_city_id",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "bk_idc_city_id",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `bk_idc_city_id` bigint NULL",
		},
		{
			Version: 31,
			Name:    "000031_t_dbm_metadata_bk_biz_id",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "bk_biz_id",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `bk_biz_id` bigint NULL",
		},
		{
			Version: 32,
			Name:    "000032_t_dbm_metadata_logical_city_id",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "logical_city_id",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `logical_city_id` bigint NULL",
		},
		{
			Version: 33,
			Name:    "000033_t_dbm_metadata_logcial_city_name",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "logcial_city_name",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `logcial_city_name` varchar(128) NULL",
		},
		{
			Version: 34,
			Name:    "000034_t_dbm_metadata_cluster",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "cluster",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `cluster` varchar(128) NULL",
		},
	}
}

func publishedSchemaStepsPart05() []schemaStep {
	return []schemaStep{
		{
			Version: 35,
			Name:    "000035_t_dbm_metadata_cluster_id",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "cluster_id",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `cluster_id` bigint NULL",
		},
		{
			Version: 36,
			Name:    "000036_t_dbm_metadata_cluster_type",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "cluster_type",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `cluster_type` varchar(128) NULL",
		},
		{
			Version: 37,
			Name:    "000037_t_dbm_metadata_machine_type",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "machine_type",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `machine_type` varchar(128) NULL",
		},
		{
			Version: 38,
			Name:    "000038_t_dbm_metadata_access_layer",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "access_layer",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `access_layer` varchar(128) NULL",
		},
		{
			Version: 39,
			Name:    "000039_t_dbm_metadata_status",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "status",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `status` varchar(128) NULL",
		},
		{
			Version: 40,
			Name:    "000040_t_dbm_metadata_instance_role",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "instance_role",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `instance_role` varchar(128) NULL",
		},
		{
			Version: 41,
			Name:    "000041_t_dbm_metadata_receiver",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "receiver",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `receiver` mediumtext NULL",
		},
		{
			Version: 42,
			Name:    "000042_t_dbm_metadata_bind_entry",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "bind_entry",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `bind_entry` mediumtext NULL",
		},
		{
			Version: 43,
			Name:    "000043_t_dbm_metadata_proxy_insts",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "proxy_insts",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `proxy_insts` mediumtext NULL",
		},
	}
}

func publishedSchemaStepsPart06() []schemaStep {
	return []schemaStep{
		{
			Version: 44,
			Name:    "000044_t_dbm_metadata_binlog_dumpers",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "binlog_dumpers",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `binlog_dumpers` mediumtext NULL",
		},
		{
			Version: 45,
			Name:    "000045_t_dbm_metadata_created_at",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "created_at",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `created_at` datetime NULL",
		},
		{
			Version: 46,
			Name:    "000046_t_dbm_metadata_updated_at",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "updated_at",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `updated_at` datetime NULL",
		},
		{
			Version: 47,
			Name:    "000047_t_dbm_metadata_deleted_at",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "deleted_at",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `deleted_at` datetime NULL",
		},
		{
			Version: 48,
			Name:    "000048_t_dbm_metadata_sync_duration",
			Table:   "t_dbm_metadata",
			Kind:    objectColumn,
			Column:  "sync_duration",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD COLUMN `sync_duration` bigint NULL",
		},
		{
			Version: 49,
			Name:    "000049_t_dbm_metadata_idx_deleted_at",
			Table:   "t_dbm_metadata",
			Kind:    objectIndex,
			Index:   "idx_deleted_at",
			Apply:   "ALTER TABLE `t_dbm_metadata` ADD INDEX `idx_deleted_at` (`deleted_at`)",
		},
		{
			Version: 50,
			Name:    "000050_create_t_skip_dbinstance",
			Table:   "t_skip_dbinstance",
			Kind:    objectTable,
			Apply: "CREATE TABLE `t_skip_dbinstance` (`bk_cloud_id` bigint NOT NULL,`bk_biz_" +
				"id` bigint NOT NULL,`instance_ip` varchar(128) NOT NULL,`instance_port` " +
				"bigint NULL,`created_at` datetime NULL,`updated_at` datetime NULL,`delet" +
				"ed_at` datetime NULL,PRIMARY KEY (`bk_cloud_id`, `bk_biz_id`, `instance_" +
				"ip`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
		},
		{
			Version: 51,
			Name:    "000051_t_skip_dbinstance_bk_cloud_id",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "bk_cloud_id",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `bk_cloud_id` bigint NULL",
		},
		{
			Version: 52,
			Name:    "000052_t_skip_dbinstance_bk_biz_id",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "bk_biz_id",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `bk_biz_id` bigint NULL",
		},
	}
}

func publishedSchemaStepsPart07() []schemaStep {
	return []schemaStep{
		{
			Version: 53,
			Name:    "000053_t_skip_dbinstance_instance_ip",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "instance_ip",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `instance_ip` varchar(128) NULL",
		},
		{
			Version: 54,
			Name:    "000054_t_skip_dbinstance_instance_port",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "instance_port",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `instance_port` bigint NULL",
		},
		{
			Version: 55,
			Name:    "000055_t_skip_dbinstance_created_at",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "created_at",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `created_at` datetime NULL",
		},
		{
			Version: 56,
			Name:    "000056_t_skip_dbinstance_updated_at",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "updated_at",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `updated_at` datetime NULL",
		},
		{
			Version: 57,
			Name:    "000057_t_skip_dbinstance_deleted_at",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumn,
			Column:  "deleted_at",
			Apply:   "ALTER TABLE `t_skip_dbinstance` ADD COLUMN `deleted_at` datetime NULL",
		},
		{
			Version: 58,
			Name:    "000058_create_t_db_switching_log",
			Table:   "t_db_switching_log",
			Kind:    objectTable,
			Apply: "CREATE TABLE `t_db_switching_log` (`id` bigint unsigned NOT NULL AUTO_IN" +
				"CREMENT,`switch_id` varchar(128) NULL,`action_scope` varchar(128) NULL,`" +
				"bk_biz_id` bigint NULL,`bk_cloud_id` bigint NULL,`db_ip` varchar(128) NU" +
				"LL,`db_port` bigint NULL,`cluster_id` bigint NULL,`cluster_name` varchar" +
				"(128) NULL,`db_type_name` varchar(128) NULL,`level` varchar(128) NULL,`c" +
				"ontent` mediumtext NULL,`created_time` datetime NULL,PRIMARY KEY (`id`))" +
				" ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
		},
		{
			Version: 59,
			Name:    "000059_t_db_switching_log_id",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "id",
			Apply: "ALTER TABLE `t_db_switching_log` ADD COLUMN `id` bigint unsigned NOT NUL" +
				"L AUTO_INCREMENT, ADD INDEX `idx_migrate_id` (`id`)",
		},
		{
			Version: 60,
			Name:    "000060_t_db_switching_log_switch_id",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "switch_id",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `switch_id` varchar(128) NULL",
		},
	}
}

func publishedSchemaStepsPart08() []schemaStep {
	return []schemaStep{
		{
			Version: 61,
			Name:    "000061_t_db_switching_log_action_scope",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "action_scope",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `action_scope` varchar(128) NULL",
		},
		{
			Version: 62,
			Name:    "000062_t_db_switching_log_bk_biz_id",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "bk_biz_id",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `bk_biz_id` bigint NULL",
		},
		{
			Version: 63,
			Name:    "000063_t_db_switching_log_bk_cloud_id",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "bk_cloud_id",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `bk_cloud_id` bigint NULL",
		},
		{
			Version: 64,
			Name:    "000064_t_db_switching_log_db_ip",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "db_ip",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `db_ip` varchar(128) NULL",
		},
		{
			Version: 65,
			Name:    "000065_t_db_switching_log_db_port",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "db_port",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `db_port` bigint NULL",
		},
		{
			Version: 66,
			Name:    "000066_t_db_switching_log_cluster_id",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "cluster_id",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `cluster_id` bigint NULL",
		},
		{
			Version: 67,
			Name:    "000067_t_db_switching_log_cluster_name",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "cluster_name",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `cluster_name` varchar(128) NULL",
		},
		{
			Version: 68,
			Name:    "000068_t_db_switching_log_db_type_name",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "db_type_name",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `db_type_name` varchar(128) NULL",
		},
		{
			Version: 69,
			Name:    "000069_t_db_switching_log_level",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "level",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `level` varchar(128) NULL",
		},
	}
}

func publishedSchemaStepsPart09() []schemaStep {
	return []schemaStep{
		{
			Version: 70,
			Name:    "000070_t_db_switching_log_content",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "content",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `content` mediumtext NULL",
		},
		{
			Version: 71,
			Name:    "000071_t_db_switching_log_created_time",
			Table:   "t_db_switching_log",
			Kind:    objectColumn,
			Column:  "created_time",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD COLUMN `created_time` datetime NULL",
		},
		{
			Version: 72,
			Name:    "000072_t_db_switching_log_idx_switch_id",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_switch_id",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_switch_id` (`switch_id`)",
		},
		{
			Version: 73,
			Name:    "000073_t_db_switching_log_idx_scope",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_scope",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_scope` (`action_scope`)",
		},
		{
			Version: 74,
			Name:    "000074_t_db_switching_log_idx_biz",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_biz",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_biz` (`bk_biz_id`)",
		},
		{
			Version: 75,
			Name:    "000075_t_db_switching_log_idx_ip_port",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_ip_port",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_ip_port` (`db_ip`, `db_port`)",
		},
		{
			Version: 76,
			Name:    "000076_t_db_switching_log_idx_cluster_id",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_cluster_id",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_cluster_id` (`cluster_id`)",
		},
		{
			Version: 77,
			Name:    "000077_t_db_switching_log_idx_cluster",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_cluster",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_cluster` (`cluster_name`)",
		},
		{
			Version: 78,
			Name:    "000078_t_db_switching_log_idx_dbtype",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_dbtype",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_dbtype` (`db_type_name`)",
		},
	}
}

func publishedSchemaStepsPart10() []schemaStep {
	return []schemaStep{
		{
			Version: 79,
			Name:    "000079_t_db_switching_log_idx_level",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_level",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_level` (`level`)",
		},
		{
			Version: 80,
			Name:    "000080_t_db_switching_log_idx_time",
			Table:   "t_db_switching_log",
			Kind:    objectIndex,
			Index:   "idx_time",
			Apply:   "ALTER TABLE `t_db_switching_log` ADD INDEX `idx_time` (`created_time`)",
		},
		{
			Version: 81,
			Name:    "000081_create_t_db_switching_snapshot_log",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectTable,
			Apply: "CREATE TABLE `t_db_switching_snapshot_log` (`id` bigint unsigned NOT NUL" +
				"L AUTO_INCREMENT,`switch_id` varchar(128) NULL,`db_type` varchar(128) NU" +
				"LL,`action_scope` varchar(128) NULL,`action` varchar(128) NULL,`strategi" +
				"es` json NULL,`bk_biz_id` bigint NULL,`bk_cloud_id` bigint NULL,`instanc" +
				"es` json NULL,`origin_instances` json NULL,`reason` varchar(128) NULL,`r" +
				"esult` mediumtext NULL,`status` varchar(128) NULL,`start_time` datetime " +
				"NULL,`finished_time` datetime NULL,PRIMARY KEY (`id`)) ENGINE=InnoDB DEF" +
				"AULT CHARSET=utf8mb4",
		},
		{
			Version: 82,
			Name:    "000082_t_db_switching_snapshot_log_id",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "id",
			Apply: "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `id` bigint unsigne" +
				"d NOT NULL AUTO_INCREMENT, ADD INDEX `idx_migrate_id` (`id`)",
		},
		{
			Version: 83,
			Name:    "000083_t_db_switching_snapshot_log_switch_id",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "switch_id",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `switch_id` varchar(128) NULL",
		},
		{
			Version: 84,
			Name:    "000084_t_db_switching_snapshot_log_db_type",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "db_type",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `db_type` varchar(128) NULL",
		},
		{
			Version: 85,
			Name:    "000085_t_db_switching_snapshot_log_action_scope",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "action_scope",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `action_scope` varchar(128) NULL",
		},
		{
			Version: 86,
			Name:    "000086_t_db_switching_snapshot_log_action",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "action",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `action` varchar(128) NULL",
		},
	}
}

func publishedSchemaStepsPart11() []schemaStep {
	return []schemaStep{
		{
			Version: 87,
			Name:    "000087_t_db_switching_snapshot_log_strategies",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "strategies",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `strategies` json NULL",
		},
		{
			Version: 88,
			Name:    "000088_t_db_switching_snapshot_log_bk_biz_id",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "bk_biz_id",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `bk_biz_id` bigint NULL",
		},
		{
			Version: 89,
			Name:    "000089_t_db_switching_snapshot_log_bk_cloud_id",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "bk_cloud_id",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `bk_cloud_id` bigint NULL",
		},
		{
			Version: 90,
			Name:    "000090_t_db_switching_snapshot_log_instances",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "instances",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `instances` json NULL",
		},
		{
			Version: 91,
			Name:    "000091_t_db_switching_snapshot_log_origin_instances",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "origin_instances",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `origin_instances` json NULL",
		},
		{
			Version: 92,
			Name:    "000092_t_db_switching_snapshot_log_reason",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "reason",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `reason` varchar(128) NULL",
		},
		{
			Version: 93,
			Name:    "000093_t_db_switching_snapshot_log_result",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "result",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `result` mediumtext NULL",
		},
		{
			Version: 94,
			Name:    "000094_t_db_switching_snapshot_log_status",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "status",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `status` varchar(128) NULL",
		},
		{
			Version: 95,
			Name:    "000095_t_db_switching_snapshot_log_start_time",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "start_time",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `start_time` datetime NULL",
		},
	}
}

func publishedSchemaStepsPart12() []schemaStep {
	return []schemaStep{
		{
			Version: 96,
			Name:    "000096_t_db_switching_snapshot_log_finished_time",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumn,
			Column:  "finished_time",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD COLUMN `finished_time` datetime NULL",
		},
		{
			Version: 97,
			Name:    "000097_t_db_switching_snapshot_log_idx_switch_id",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_switch_id",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD UNIQUE INDEX `idx_switch_id` (`switch_id`)",
		},
		{
			Version: 98,
			Name:    "000098_t_db_switching_snapshot_log_idx_db_type",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_db_type",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD INDEX `idx_db_type` (`db_type`)",
		},
		{
			Version: 99,
			Name:    "000099_t_db_switching_snapshot_log_idx_scope",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_scope",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD INDEX `idx_scope` (`action_scope`)",
		},
		{
			Version: 100,
			Name:    "000100_t_db_switching_snapshot_log_idx_action",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_action",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD INDEX `idx_action` (`action`)",
		},
		{
			Version: 101,
			Name:    "000101_t_db_switching_snapshot_log_idx_biz",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_biz",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD INDEX `idx_biz` (`bk_biz_id`)",
		},
		{
			Version: 102,
			Name:    "000102_t_db_switching_snapshot_log_idx_status",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_status",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD INDEX `idx_status` (`status`)",
		},
		{
			Version: 103,
			Name:    "000103_t_db_switching_snapshot_log_idx_time",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectIndex,
			Index:   "idx_time",
			Apply:   "ALTER TABLE `t_db_switching_snapshot_log` ADD INDEX `idx_time` (`start_time`)",
		},
	}
}

func publishedSchemaStepsPart13() []schemaStep {
	return []schemaStep{
		{
			Version: 104,
			Name:    "000104_create_t_db_switching_strategy",
			Table:   "t_db_switching_strategy",
			Kind:    objectTable,
			Apply: "CREATE TABLE `t_db_switching_strategy` (`id` bigint NOT NULL AUTO_INCREM" +
				"ENT,`status` varchar(32) NULL,`name` varchar(128) NULL,`bk_biz_id` bigin" +
				"t NOT NULL,`trigger_event_name` varchar(128) NOT NULL,`trigger_event_nam" +
				"e_reason` bigint NOT NULL,`trigger_count` bigint NULL,`priority` bigint " +
				"NULL,`scope` varchar(32) NULL,`action` varchar(32) NULL,`description` me" +
				"diumtext NULL,`created_at` datetime NULL,`updated_at` datetime NULL,`del" +
				"eted_at` datetime NULL,PRIMARY KEY (`id`, `bk_biz_id`, `trigger_event_na" +
				"me`, `trigger_event_name_reason`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
		},
		{
			Version: 105,
			Name:    "000105_t_db_switching_strategy_id",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "id",
			Apply: "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `id` bigint NOT NULL AU" +
				"TO_INCREMENT, ADD INDEX `idx_migrate_id` (`id`)",
		},
		{
			Version: 106,
			Name:    "000106_t_db_switching_strategy_status",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "status",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `status` varchar(32) NULL",
		},
		{
			Version: 107,
			Name:    "000107_t_db_switching_strategy_name",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "name",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `name` varchar(128) NULL",
		},
		{
			Version: 108,
			Name:    "000108_t_db_switching_strategy_bk_biz_id",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "bk_biz_id",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `bk_biz_id` bigint NULL",
		},
		{
			Version: 109,
			Name:    "000109_t_db_switching_strategy_trigger_event_name",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "trigger_event_name",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `trigger_event_name` varchar(128) NULL",
		},
		{
			Version: 110,
			Name:    "000110_t_db_switching_strategy_trigger_event_name_reason",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "trigger_event_name_reason",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `trigger_event_name_reason` bigint NULL",
		},
		{
			Version: 111,
			Name:    "000111_t_db_switching_strategy_trigger_count",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "trigger_count",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `trigger_count` bigint NULL",
		},
	}
}

func publishedSchemaStepsPart14() []schemaStep {
	return []schemaStep{
		{
			Version: 112,
			Name:    "000112_t_db_switching_strategy_priority",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "priority",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `priority` bigint NULL",
		},
		{
			Version: 113,
			Name:    "000113_t_db_switching_strategy_scope",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "scope",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `scope` varchar(32) NULL",
		},
		{
			Version: 114,
			Name:    "000114_t_db_switching_strategy_action",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "action",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `action` varchar(32) NULL",
		},
		{
			Version: 115,
			Name:    "000115_t_db_switching_strategy_description",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "description",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `description` mediumtext NULL",
		},
		{
			Version: 116,
			Name:    "000116_t_db_switching_strategy_created_at",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "created_at",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `created_at` datetime NULL",
		},
		{
			Version: 117,
			Name:    "000117_t_db_switching_strategy_updated_at",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "updated_at",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `updated_at` datetime NULL",
		},
		{
			Version: 118,
			Name:    "000118_t_db_switching_strategy_deleted_at",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumn,
			Column:  "deleted_at",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD COLUMN `deleted_at` datetime NULL",
		},
		{
			Version: 119,
			Name:    "000119_t_db_switching_strategy_idx_name",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_name",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD UNIQUE INDEX `idx_name` (`name`, `bk_biz_id`)",
		},
		{
			Version: 120,
			Name:    "000120_t_db_switching_strategy_idx_trigger_event_name",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_trigger_event_name",
			Apply: "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_trigger_event_name`" +
				" (`trigger_event_name`)",
		},
	}
}

func publishedSchemaStepsPart15() []schemaStep {
	return []schemaStep{
		{
			Version: 121,
			Name:    "000121_t_db_switching_strategy_idx_trigger_event_name_reason",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_trigger_event_name_reason",
			Apply: "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_trigger_event_name_" +
				"reason` (`trigger_event_name_reason`)",
		},
		{
			Version: 122,
			Name:    "000122_t_db_switching_strategy_idx_description",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_description",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_description` (`description`(255))",
		},
		{
			Version: 123,
			Name:    "000123_t_db_switching_strategy_idx_created_at",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_created_at",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_created_at` (`created_at`)",
		},
		{
			Version: 124,
			Name:    "000124_t_db_switching_strategy_idx_updated_at",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_updated_at",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_updated_at` (`updated_at`)",
		},
		{
			Version: 125,
			Name:    "000125_t_db_switching_strategy_idx_deleted_at",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_deleted_at",
			Apply:   "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_deleted_at` (`deleted_at`)",
		},
		{
			Version: 126,
			Name:    "000126_t_dbha_status_machine_id_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "machine_id",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`machine_id`",
		},
		{
			Version: 127,
			Name:    "000127_t_dbha_status_bk_cloud_id_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "bk_cloud_id",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`bk_cloud_id`",
		},
		{
			Version: 128,
			Name:    "000128_t_dbha_status_db_ip_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "db_ip",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`db_ip`",
		},
		{
			Version: 129,
			Name:    "000129_t_dbha_status_db_port_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "db_port",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`db_port`",
		},
	}
}

func publishedSchemaStepsPart16() []schemaStep {
	return []schemaStep{
		{
			Version: 130,
			Name:    "000130_t_dbha_status_harvest_type_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "harvest_type",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`harvest_type`",
		},
		{
			Version: 131,
			Name:    "000131_t_dbha_status_sequence_id_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "sequence_id",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`sequence_id`",
		},
		{
			Version: 132,
			Name:    "000132_t_dbha_status_agent_id_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "agent_id",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`agent_id`",
		},
		{
			Version: 133,
			Name:    "000133_t_dbha_status_ips_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "ips",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`ips`",
		},
		{
			Version: 134,
			Name:    "000134_t_dbha_status_message_id_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "message_id",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`message_id`",
		},
		{
			Version: 135,
			Name:    "000135_t_dbha_status_service_id_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "service_id",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`service_id`",
		},
		{
			Version: 136,
			Name:    "000136_t_dbha_status_db_type_name_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "db_type_name",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`db_type_name`",
		},
		{
			Version: 137,
			Name:    "000137_t_dbha_status_access_layer_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "access_layer",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`access_layer`",
		},
		{
			Version: 138,
			Name:    "000138_t_dbha_status_cluster_type_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "cluster_type",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`cluster_type`",
		},
	}
}

func publishedSchemaStepsPart17() []schemaStep {
	return []schemaStep{
		{
			Version: 139,
			Name:    "000139_t_dbha_status_machine_type_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "machine_type",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`machine_type`",
		},
		{
			Version: 140,
			Name:    "000140_t_dbha_status_instance_role_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "instance_role",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`instance_role`",
		},
		{
			Version: 141,
			Name:    "000141_t_dbha_status_report_timestamp_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "report_timestamp",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`report_timestamp`",
		},
		{
			Version: 142,
			Name:    "000142_t_dbha_status_host_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "host",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`host`",
		},
		{
			Version: 143,
			Name:    "000143_t_dbha_status_probe_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "probe",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`probe`",
		},
		{
			Version: 144,
			Name:    "000144_t_dbha_status_event_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "event",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`event`",
		},
		{
			Version: 145,
			Name:    "000145_t_dbha_status_data_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "data",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`data`",
		},
		{
			Version: 146,
			Name:    "000146_t_dbha_status_created_at_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "created_at",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`created_at`",
		},
		{
			Version: 147,
			Name:    "000147_t_dbha_status_updated_at_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "updated_at",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`updated_at`",
		},
	}
}

func publishedSchemaStepsPart18() []schemaStep {
	return []schemaStep{
		{
			Version: 148,
			Name:    "000148_t_dbha_status_deleted_at_definition",
			Table:   "t_dbha_status",
			Kind:    objectColumnDef,
			Column:  "deleted_at",
			Apply:   "CONVERGE COLUMN `t_dbha_status`.`deleted_at`",
		},
		{
			Version: 149,
			Name:    "000149_t_dbha_status_primary_key",
			Table:   "t_dbha_status",
			Kind:    objectPrimaryKey,
			Apply:   "CONVERGE PRIMARY KEY `t_dbha_status`",
		},
		{
			Version: 150,
			Name:    "000150_t_dbm_metadata_bk_cloud_id_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "bk_cloud_id",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`bk_cloud_id`",
		},
		{
			Version: 151,
			Name:    "000151_t_dbm_metadata_ip_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "ip",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`ip`",
		},
		{
			Version: 152,
			Name:    "000152_t_dbm_metadata_port_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "port",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`port`",
		},
		{
			Version: 153,
			Name:    "000153_t_dbm_metadata_admin_port_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "admin_port",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`admin_port`",
		},
		{
			Version: 154,
			Name:    "000154_t_dbm_metadata_bk_idc_city_id_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "bk_idc_city_id",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`bk_idc_city_id`",
		},
		{
			Version: 155,
			Name:    "000155_t_dbm_metadata_bk_biz_id_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "bk_biz_id",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`bk_biz_id`",
		},
		{
			Version: 156,
			Name:    "000156_t_dbm_metadata_logical_city_id_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "logical_city_id",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`logical_city_id`",
		},
	}
}

func publishedSchemaStepsPart19() []schemaStep {
	return []schemaStep{
		{
			Version: 157,
			Name:    "000157_t_dbm_metadata_logcial_city_name_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "logcial_city_name",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`logcial_city_name`",
		},
		{
			Version: 158,
			Name:    "000158_t_dbm_metadata_cluster_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "cluster",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`cluster`",
		},
		{
			Version: 159,
			Name:    "000159_t_dbm_metadata_cluster_id_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "cluster_id",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`cluster_id`",
		},
		{
			Version: 160,
			Name:    "000160_t_dbm_metadata_cluster_type_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "cluster_type",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`cluster_type`",
		},
		{
			Version: 161,
			Name:    "000161_t_dbm_metadata_machine_type_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "machine_type",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`machine_type`",
		},
		{
			Version: 162,
			Name:    "000162_t_dbm_metadata_access_layer_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "access_layer",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`access_layer`",
		},
		{
			Version: 163,
			Name:    "000163_t_dbm_metadata_status_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "status",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`status`",
		},
		{
			Version: 164,
			Name:    "000164_t_dbm_metadata_instance_role_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "instance_role",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`instance_role`",
		},
		{
			Version: 165,
			Name:    "000165_t_dbm_metadata_receiver_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "receiver",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`receiver`",
		},
	}
}

func publishedSchemaStepsPart20() []schemaStep {
	return []schemaStep{
		{
			Version: 166,
			Name:    "000166_t_dbm_metadata_bind_entry_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "bind_entry",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`bind_entry`",
		},
		{
			Version: 167,
			Name:    "000167_t_dbm_metadata_proxy_insts_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "proxy_insts",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`proxy_insts`",
		},
		{
			Version: 168,
			Name:    "000168_t_dbm_metadata_binlog_dumpers_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "binlog_dumpers",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`binlog_dumpers`",
		},
		{
			Version: 169,
			Name:    "000169_t_dbm_metadata_created_at_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "created_at",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`created_at`",
		},
		{
			Version: 170,
			Name:    "000170_t_dbm_metadata_updated_at_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "updated_at",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`updated_at`",
		},
		{
			Version: 171,
			Name:    "000171_t_dbm_metadata_deleted_at_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "deleted_at",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`deleted_at`",
		},
		{
			Version: 172,
			Name:    "000172_t_dbm_metadata_sync_duration_definition",
			Table:   "t_dbm_metadata",
			Kind:    objectColumnDef,
			Column:  "sync_duration",
			Apply:   "CONVERGE COLUMN `t_dbm_metadata`.`sync_duration`",
		},
		{
			Version: 173,
			Name:    "000173_t_skip_dbinstance_bk_cloud_id_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "bk_cloud_id",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`bk_cloud_id`",
		},
		{
			Version: 174,
			Name:    "000174_t_skip_dbinstance_bk_biz_id_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "bk_biz_id",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`bk_biz_id`",
		},
	}
}

func publishedSchemaStepsPart21() []schemaStep {
	return []schemaStep{
		{
			Version: 175,
			Name:    "000175_t_skip_dbinstance_instance_ip_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "instance_ip",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`instance_ip`",
		},
		{
			Version: 176,
			Name:    "000176_t_skip_dbinstance_instance_port_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "instance_port",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`instance_port`",
		},
		{
			Version: 177,
			Name:    "000177_t_skip_dbinstance_created_at_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "created_at",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`created_at`",
		},
		{
			Version: 178,
			Name:    "000178_t_skip_dbinstance_updated_at_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "updated_at",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`updated_at`",
		},
		{
			Version: 179,
			Name:    "000179_t_skip_dbinstance_deleted_at_definition",
			Table:   "t_skip_dbinstance",
			Kind:    objectColumnDef,
			Column:  "deleted_at",
			Apply:   "CONVERGE COLUMN `t_skip_dbinstance`.`deleted_at`",
		},
		{
			Version: 180,
			Name:    "000180_t_db_switching_log_id_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "id",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`id`",
		},
		{
			Version: 181,
			Name:    "000181_t_db_switching_log_switch_id_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "switch_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`switch_id`",
		},
		{
			Version: 182,
			Name:    "000182_t_db_switching_log_action_scope_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "action_scope",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`action_scope`",
		},
		{
			Version: 183,
			Name:    "000183_t_db_switching_log_bk_biz_id_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "bk_biz_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`bk_biz_id`",
		},
	}
}

func publishedSchemaStepsPart22() []schemaStep {
	return []schemaStep{
		{
			Version: 184,
			Name:    "000184_t_db_switching_log_bk_cloud_id_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "bk_cloud_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`bk_cloud_id`",
		},
		{
			Version: 185,
			Name:    "000185_t_db_switching_log_db_ip_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "db_ip",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`db_ip`",
		},
		{
			Version: 186,
			Name:    "000186_t_db_switching_log_db_port_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "db_port",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`db_port`",
		},
		{
			Version: 187,
			Name:    "000187_t_db_switching_log_cluster_id_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "cluster_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`cluster_id`",
		},
		{
			Version: 188,
			Name:    "000188_t_db_switching_log_cluster_name_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "cluster_name",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`cluster_name`",
		},
		{
			Version: 189,
			Name:    "000189_t_db_switching_log_db_type_name_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "db_type_name",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`db_type_name`",
		},
		{
			Version: 190,
			Name:    "000190_t_db_switching_log_level_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "level",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`level`",
		},
		{
			Version: 191,
			Name:    "000191_t_db_switching_log_content_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "content",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`content`",
		},
		{
			Version: 192,
			Name:    "000192_t_db_switching_log_created_time_definition",
			Table:   "t_db_switching_log",
			Kind:    objectColumnDef,
			Column:  "created_time",
			Apply:   "CONVERGE COLUMN `t_db_switching_log`.`created_time`",
		},
	}
}

func publishedSchemaStepsPart23() []schemaStep {
	return []schemaStep{
		{
			Version: 193,
			Name:    "000193_t_db_switching_snapshot_log_id_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "id",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`id`",
		},
		{
			Version: 194,
			Name:    "000194_t_db_switching_snapshot_log_switch_id_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "switch_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`switch_id`",
		},
		{
			Version: 195,
			Name:    "000195_t_db_switching_snapshot_log_db_type_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "db_type",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`db_type`",
		},
		{
			Version: 196,
			Name:    "000196_t_db_switching_snapshot_log_action_scope_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "action_scope",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`action_scope`",
		},
		{
			Version: 197,
			Name:    "000197_t_db_switching_snapshot_log_action_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "action",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`action`",
		},
		{
			Version: 198,
			Name:    "000198_t_db_switching_snapshot_log_strategies_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "strategies",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`strategies`",
		},
		{
			Version: 199,
			Name:    "000199_t_db_switching_snapshot_log_bk_biz_id_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "bk_biz_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`bk_biz_id`",
		},
		{
			Version: 200,
			Name:    "000200_t_db_switching_snapshot_log_bk_cloud_id_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "bk_cloud_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`bk_cloud_id`",
		},
		{
			Version: 201,
			Name:    "000201_t_db_switching_snapshot_log_instances_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "instances",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`instances`",
		},
	}
}

func publishedSchemaStepsPart24() []schemaStep {
	return []schemaStep{
		{
			Version: 202,
			Name:    "000202_t_db_switching_snapshot_log_origin_instances_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "origin_instances",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`origin_instances`",
		},
		{
			Version: 203,
			Name:    "000203_t_db_switching_snapshot_log_reason_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "reason",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`reason`",
		},
		{
			Version: 204,
			Name:    "000204_t_db_switching_snapshot_log_result_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "result",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`result`",
		},
		{
			Version: 205,
			Name:    "000205_t_db_switching_snapshot_log_status_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "status",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`status`",
		},
		{
			Version: 206,
			Name:    "000206_t_db_switching_snapshot_log_start_time_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "start_time",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`start_time`",
		},
		{
			Version: 207,
			Name:    "000207_t_db_switching_snapshot_log_finished_time_definition",
			Table:   "t_db_switching_snapshot_log",
			Kind:    objectColumnDef,
			Column:  "finished_time",
			Apply:   "CONVERGE COLUMN `t_db_switching_snapshot_log`.`finished_time`",
		},
		{
			Version: 208,
			Name:    "000208_t_db_switching_strategy_id_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "id",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`id`",
		},
		{
			Version: 209,
			Name:    "000209_t_db_switching_strategy_status_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "status",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`status`",
		},
		{
			Version: 210,
			Name:    "000210_t_db_switching_strategy_name_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "name",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`name`",
		},
	}
}

func publishedSchemaStepsPart25() []schemaStep {
	return []schemaStep{
		{
			Version: 211,
			Name:    "000211_t_db_switching_strategy_bk_biz_id_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "bk_biz_id",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`bk_biz_id`",
		},
		{
			Version: 212,
			Name:    "000212_t_db_switching_strategy_trigger_event_name_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "trigger_event_name",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`trigger_event_name`",
		},
		{
			Version: 213,
			Name:    "000213_t_db_switching_strategy_trigger_event_name_reason_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "trigger_event_name_reason",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`trigger_event_name_reason`",
		},
		{
			Version: 214,
			Name:    "000214_t_db_switching_strategy_trigger_count_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "trigger_count",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`trigger_count`",
		},
		{
			Version: 215,
			Name:    "000215_t_db_switching_strategy_priority_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "priority",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`priority`",
		},
		{
			Version: 216,
			Name:    "000216_t_db_switching_strategy_scope_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "scope",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`scope`",
		},
		{
			Version: 217,
			Name:    "000217_t_db_switching_strategy_action_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "action",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`action`",
		},
		{
			Version: 218,
			Name:    "000218_t_db_switching_strategy_description_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "description",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`description`",
		},
		{
			Version: 219,
			Name:    "000219_t_db_switching_strategy_created_at_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "created_at",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`created_at`",
		},
	}
}

func publishedSchemaStepsPart26() []schemaStep {
	return []schemaStep{
		{
			Version: 220,
			Name:    "000220_t_db_switching_strategy_updated_at_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "updated_at",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`updated_at`",
		},
		{
			Version: 221,
			Name:    "000221_t_db_switching_strategy_deleted_at_definition",
			Table:   "t_db_switching_strategy",
			Kind:    objectColumnDef,
			Column:  "deleted_at",
			Apply:   "CONVERGE COLUMN `t_db_switching_strategy`.`deleted_at`",
		},
		{
			Version: 222,
			Name:    "000222_t_db_switching_strategy_primary_key",
			Table:   "t_db_switching_strategy",
			Kind:    objectPrimaryKey,
			Apply:   "CONVERGE PRIMARY KEY `t_db_switching_strategy`",
		}}
}

func publishedSchemaStepsPart27() []schemaStep {
	return []schemaStep{
		{
			Version: 223,
			Name:    "000223_t_db_switching_strategy_idx_biz_event_reason",
			Table:   "t_db_switching_strategy",
			Kind:    objectIndex,
			Index:   "idx_biz_event_reason",
			Apply: "ALTER TABLE `t_db_switching_strategy` ADD UNIQUE INDEX `idx_biz_event_reason` " +
				"(`bk_biz_id`, `trigger_event_name`, `trigger_event_name_reason`)",
		}}
}
