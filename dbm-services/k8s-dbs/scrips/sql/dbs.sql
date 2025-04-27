-- Create a database and set character set and collation
CREATE DATABASE IF NOT EXISTS bkbase_dbs;
USE bkbase_dbs;

SET NAMES utf8;

--
-- Table structure for table tb_k8s_crd_storageaddon
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_storageaddon (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    addon_name varchar(100) NOT NULL UNIQUE COMMENT '存储插件名称',
    addon_category varchar(100) NOT NULL COMMENT '存储插件类型 Kv/Document/Oltp/Olap/Graph/Time-Series/Vector/Full-Text',
    addon_type varchar(100) NOT NULL COMMENT '存储插件种类 MySql/Oracle/Redis...',
    metadata text DEFAULT NULL COMMENT 'metadata定义',
    spec text DEFAULT NULL COMMENT 'spec定义',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) Null COMMENT '存储插件描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储插件相关信息的表';

--
-- Table structure for table tb_k8s_crd_clusterdefinition
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_clusterdefinition (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    addon_id bigint NOT NULL COMMENT '关联 k8s_crd_storageaddon 主键 id',
    clusterdefinition_name varchar(100) NOT NULL COMMENT '集群定义名称',
    metadata text DEFAULT NULL COMMENT 'metadata定义',
    spec text DEFAULT NULL COMMENT 'spec定义',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) COMMENT '集群定义描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储集群定义相关信息的表';

--
-- Table structure for table tb_k8s_crd_componentdefinition
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_componentdefinition (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    componentdefinition_name varchar(100) NOT NULL COMMENT '组件定义名称',
    default_version varchar(100) NOT NULL COMMENT '默认版本',
    metadata text DEFAULT NULL COMMENT 'metadata定义',
    spec text DEFAULT NULL COMMENT 'spec定义',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) COMMENT '组件定义描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储组件定义相关信息的表';

--
-- Table structure for table tb_k8s_crd_componentversion
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_componentversion (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    componentdefinition_id bigint COMMENT '关联 tb_k8s_crd_componentdefinition 主键 id',
    componentversion_name varchar(100) NOT NULL COMMENT '组件版本名称',
    metadata text DEFAULT NULL COMMENT 'metadata定义',
    spec text DEFAULT NULL COMMENT 'spec定义',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) COMMENT '组件版本描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储组件版本相关信息的表';

--
-- Table structure for table tb_k8s_crd_cluster
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_cluster (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    k8s_cluster_config_id bigint NOT NULL COMMENT '关联 tb_k8s_cluster_config 主键 id',
    request_id varchar(50) NOT NULL COMMENT 'tb_cluster_request_record 表的请求 Id',
    addon_id bigint NOT NULL COMMENT '关联 k8s_crd_storageaddon 主键 id',
    cluster_name varchar(100) NOT NULL COMMENT '集群名称',
    namespace varchar(100) NOT NULL COMMENT '集群所在的命名空间',
    status varchar(100) COMMENT '集群状态 Abnormal/Creating/Failed/Running/Updating/Stopped/Deleted',
    description varchar(100) COMMENT '集群描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储集群相关信息的表';

--
-- Table structure for table tb_k8s_crd_component
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_component (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    crd_cluster_id bigint NOT NULL COMMENT '关联 k8s_crd_cluster 主键 id',
    component_name varchar(100) NOT NULL COMMENT '组件名称',
    status varchar(100) COMMENT '组件状态 Abnormal/Creating/Failed/Running/Updating/Stopped/Deleted',
    description varchar(100) COMMENT '组件描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储组件相关信息的表';

--
-- Table structure for table tb_k8s_crd_cluster_service
--
CREATE TABLE IF NOT EXISTS tb_k8s_cluster_service (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    crd_cluster_id bigint NOT NULL COMMENT '关联 k8s_crd_cluster 主键 id',
    component_name varchar(100) NOT NULL COMMENT '组件名称',
    service_name varchar(100) NOT NULL COMMENT 'service 名称',
    service_type varchar(32) NOT NULL COMMENT 'service类型 CLusterIP/NodePort/LoadBalancer',
    annotations varchar(512) COMMENT 'service annotation',
    internal_addrs varchar(255) COMMENT '内部访问地址。如果有多个端口，用分号隔开，比如 xx.xx.xx.xx:8081;xx.xx.xx:8082',
    external_addrs varchar(255) COMMENT '外部访问地址。如果有多个端口，用分号隔开，比如 xx.xx.xx.xx:8081;xx.xx.xx:8082',
    domains varchar(255) COMMENT '域名信息。如果有多个域名，用分号隔开，比如 domain_name_1;domain_name_2',
    description varchar(100) COMMENT '服务描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储集群组件访问入口相关信息的表';

--
-- Table structure for table tb_cluster_request_record
--
CREATE TABLE IF NOT EXISTS tb_cluster_request_record (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    request_id varchar(50) NOT NULL COMMENT '请求Id，使用全局的UUID',
    request_type varchar(50) NOT NULL COMMENT '操作记录类型 Create/Delete/Restart/Start/Stop/Switchover/Upgrade/HorizontalScaling/VerticalScaling/VolumeExpansion',
    request_params text COMMENT '操作记录请求信息',
    status varchar(100) COMMENT '操作记录请求状态 Cancelled/Cancelling/Creating/Failed/Pending/Running/Succeed',
    description varchar(100) COMMENT '操作记录描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '记录用户集群操作记录（排查检索）';

--
-- Table structure for table tb_k8s_crd_opsrequest
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_opsrequest (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    crd_cluster_id bigint NOT NULL COMMENT '关联 k8s_crd_cluster 主键 id',
    k8s_cluster_config_id bigint NOT NULL COMMENT '关联 tb_k8s_cluster_config 主键 id',
    request_id varchar(50) NOT NULL COMMENT 'tb_cluster_request_record 表的请求 Id',
    opsrequest_name varchar(100) NOT NULL COMMENT '操作请求名称',
    opsrequest_type varchar(100) COMMENT '操作类型 Restart/Start/Stop/Switchover/Upgrade/HorizontalScaling/VerticalScaling/VolumeExpansion',
    metadata text DEFAULT NULL COMMENT 'metadata定义',
    spec text DEFAULT NULL COMMENT 'spec定义',
    status varchar(100) COMMENT '操作请求状态 Cancelled/Cancelling/Creating/Failed/Pending/Running/Succeed',
    description varchar(100) COMMENT '操作请求描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储操作请求相关信息的表';

--
-- Table structure for table tb_k8s_cluster_config
--
CREATE TABLE IF NOT EXISTS tb_k8s_cluster_config (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    cluster_name VARCHAR(255) NOT NULL UNIQUE COMMENT 'k8s 集群名称',
    api_server_url VARCHAR(255) NOT NULL COMMENT 'k8s API Server 的 URL',
    ca_cert text COMMENT 'k8s API Server CA 证书-base64 encode',
    client_cert text COMMENT '客户端证书-base64 encode',
    client_key text COMMENT '客户端密钥-base64 encode',
    token text COMMENT 'Token 认证的 Bearer Token',
    username VARCHAR(255) COMMENT 'Basic Auth 的 username',
    password VARCHAR(255) COMMENT 'Basic Auth 的 password',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    description varchar(100) COMMENT '描述',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT 'k8s 集群连接信息';
