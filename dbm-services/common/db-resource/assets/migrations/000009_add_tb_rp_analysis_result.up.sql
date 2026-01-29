CREATE TABLE IF NOT EXISTS `tb_rp_analysis_result` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `bill_id` varchar(128) NOT NULL COMMENT '单据ID（唯一键）',
    `apply_params` json NOT NULL COMMENT '申请参数',
    `analysis_result` json COMMENT '分析结果（JSON格式）',
    `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '分析状态: pending/running/completed/failed',
    `error_msg` text COMMENT '错误信息',
    `duration` varchar(32) COMMENT '分析耗时',
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_bill_id` (`bill_id`),
    KEY `idx_status` (`status`),
    KEY `idx_create_time` (`create_time`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '资源申请智能分析结果表';
