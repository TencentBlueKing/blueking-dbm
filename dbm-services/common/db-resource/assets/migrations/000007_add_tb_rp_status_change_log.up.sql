CREATE TABLE IF NOT EXISTS `tb_rp_status_change_log` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `bk_host_id` int(11) NOT NULL COMMENT 'bk主机ID',
    `ip` varchar(20) NOT NULL COMMENT 'IP地址',
    `bk_cloud_id` int(11) NOT NULL COMMENT '云区域ID',
    `old_status` varchar(20) NOT NULL COMMENT '原状态',
    `new_status` varchar(20) NOT NULL COMMENT '新状态',
    `change_reason` varchar(50) NOT NULL COMMENT '变更原因类型',
    `reason_detail` text COMMENT '详细原因描述',
    `reason_context` json COMMENT '变更上下文信息',
    `operator` varchar(64) NOT NULL DEFAULT 'system' COMMENT '操作者',
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_host_id` (`bk_host_id`),
    KEY `idx_ip` (`ip`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8;
