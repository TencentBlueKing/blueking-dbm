-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

--
-- Table structure for table tb_k8s_cluster_addons
--
CREATE TABLE IF NOT EXISTS tb_k8s_crd_cluster_tag (
    id bigint PRIMARY KEY AUTO_INCREMENT COMMENT '主键 id',
    crd_cluster_id bigint NOT NULL COMMENT '关联 k8s_crd_cluster 主键 id',
    cluster_tag VARCHAR(32) DEFAULT '' COMMENT 'k8s 集群标签',
    active tinyint(1) NOT NULL DEFAULT 1 COMMENT '0:无效，1:有效',
    created_by varchar(50) NOT NULL COMMENT '创建者',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by varchar(50) NOT NULL COMMENT '更新者',
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT '存储集群的标签信息表';