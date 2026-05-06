-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

--
-- Table structure for table tb_addon_category
--
CREATE TABLE IF NOT EXISTS tb_addon_category (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    category_name varchar(32) NOT NULL COMMENT '插件分类名称',
    category_alias varchar(32) NOT NULL COMMENT '插件分类别名',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) Null COMMENT '描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '插件分类表';

--
-- Table structure for table tb_addon_category
--
CREATE TABLE IF NOT EXISTS tb_addon_type (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    category_id bigint NOT NULL COMMENT '插件分类 Id',
    type_name varchar(32) NOT NULL COMMENT '插件类型名称',
    type_alias varchar(32) NOT NULL COMMENT '插件类型别名',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) Null COMMENT '描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '插件类型表';