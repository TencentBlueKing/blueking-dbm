-- Create a database and set character set and collation
CREATE DATABASE IF NOT EXISTS bkbase_dbs;
USE bkbase_dbs;

SET NAMES utf8;

--
-- Table structure for table tb_addon_spec_plan
--
CREATE TABLE IF NOT EXISTS tb_addon_spec_plan (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    addon_id bigint NOT NULL COMMENT '关联 k8s_crd_storageaddon 主键 id',
    addon_topology varchar(32) NOT NULL DEFAULT '' COMMENT 'addon 拓扑类型',
    spec_level varchar(32) NOT NULL DEFAULT 'basic' COMMENT '规格 basic/standard/premium',
    spec_level_alias varchar(32) NOT NULL DEFAULT '' COMMENT '规格别名 基础/标准/高配',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) Null COMMENT '存储插件描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储套餐配置表';

--
-- Table structure for table tb_component_spec_plan
--
CREATE TABLE IF NOT EXISTS tb_component_spec_plan (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    addon_spec_plan_id bigint NOT NULL COMMENT '关联 tb_addon_spec_plan 主键 id',
    component_name varchar(32) NOT NULL COMMENT '组件名称',
    cpu_cores int DEFAULT NULL COMMENT 'cpu 配额（核心数）',
    memory_gb int DEFAULT NULL COMMENT '内存配额（GB）',
    disk_size_gb int DEFAULT NULL COMMENT '磁盘配额（GB）',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) Null COMMENT '存储插件描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储套餐组件配置表';