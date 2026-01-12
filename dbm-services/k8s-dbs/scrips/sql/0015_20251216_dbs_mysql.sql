-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- 创建组件参数配置表
CREATE TABLE IF NOT EXISTS tb_addon_params_config (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    addon_id BIGINT UNSIGNED NOT NULL COMMENT '关联 tb_k8s_crd_storageaddon 表的 ID',
    service_version VARCHAR(32) NOT NULL COMMENT '服务版本: 1.93.10-2.0.0',
    component_name VARCHAR(32) NOT NULL COMMENT '组件名: vminsert',
    param_name VARCHAR(64) NOT NULL COMMENT '参数名',
    param_type ENUM('STRING', 'INTEGER', 'BOOLEAN') DEFAULT 'STRING' COMMENT '参数类型',
    default_value VARCHAR(64) DEFAULT NULL COMMENT '参数默认值',
    active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_by VARCHAR(50) NOT NULL DEFAULT 'system' COMMENT '创建人',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(50) NOT NULL DEFAULT 'system' COMMENT '更新人',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组件参数配置表';
