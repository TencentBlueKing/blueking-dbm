-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

--
-- Table structure for table tb_addon_topology
--
CREATE TABLE IF NOT EXISTS tb_addon_topology (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    addon_name varchar(32) NOT NULL COMMENT '存储插件名称',
    addon_category varchar(32) NOT NULL COMMENT '存储插件类型 KeyValue/Document/RDBMS/OLAP/Graph/TimeSeries/Vector/FullText/ObjectStorage',
    addon_type varchar(32) NOT NULL COMMENT '存储插件种类 MySql/Oracle/Redis...',
    addon_version varchar(32) NOT NULL COMMENT '存储插件大版本',
    topology_name varchar(32) NOT NULL COMMENT '拓扑名称',
    topology_alias varchar(32) NOT NULL COMMENT '拓扑别名',
    is_default tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否是默认模式，0:不是，1:是',
    components text NOT NULL COMMENT '组件列表',
    relations text NOT NULL COMMENT '组件关系描述',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) Null COMMENT '存储插件描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储插件拓扑定义表';

