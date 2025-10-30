-- Spider 建表语句的反向测试用例（应该触发检查错误）
-- 参考: spider_rule.go 中的 SpiderCreateTableRule
USE test_db;
-- 在 Spider 环境中创建 不允许为null的列被设置为默认值
CREATE TABLE `spider_invalid_1` (
    `ip` varchar(100) DEFAULT NULL,
    KEY `ix_ip` (`ip`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8;
-- 只有一个普通索引的时候，只能为not null 
CREATE TABLE `spider_invalid_2` (`ip` varchar(100), KEY `ix_ip` (`ip`)) ENGINE = InnoDB DEFAULT CHARSET = utf8;
-- 如果多个唯一健（含主键),shard_key只能是其中的共同部分；否则无法建表
CREATE TABLE `spider_invalid_3` (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    code TINYINT UNSIGNED NOT NULL,
    name CHAR(20) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (id, name)
) COMMENT = 'shard_key "name"';
-- 如果多个普通索引，则必须指定shard_key（Tdbctl上作的限制）
CREATE TABLE `spider_invalid_4` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code` TINYINT UNSIGNED NOT NULL,
    `name` CHAR(20) NOT NULL,
    KEY `a` (`id`),
    KEY `b` (`name`)
);
-- 如果多个唯一健（含主键),shard_key只能是其中的共同部分；否则无法建表
CREATE TABLE `spider_invalid_5` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code` TINYINT UNSIGNED NOT NULL,
    `name` CHAR(20) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_name` (`name`)
) COMMENT = 'shard_key "name"';