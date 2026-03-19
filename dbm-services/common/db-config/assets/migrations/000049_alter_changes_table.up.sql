
ALTER TABLE `tb_conf_item_changes`
    MODIFY COLUMN `before_image` text NOT NULL DEFAULT '' COMMENT '变更前快照（JSON）',
    MODIFY COLUMN `after_image` text NOT NULL DEFAULT '' COMMENT '变更后快照（JSON）';

ALTER TABLE `tb_conf_name_changes`
    MODIFY COLUMN `before_image` text NOT NULL DEFAULT '' COMMENT '变更前快照（JSON）',
    MODIFY COLUMN `after_image` text NOT NULL DEFAULT '' COMMENT '变更后快照（JSON）';