SET NAMES utf8;
CREATE TABLE `partition_customization_config` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `bk_biz_id` int(11) NOT NULL,
    `immute_domain` varchar(255) NOT NULL DEFAULT '',
    `partition_column` varchar(255) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`),
    KEY `bk_biz_id` (`bk_biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
