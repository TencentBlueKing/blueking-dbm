-- 测试 Spider 特定的建表语句
-- 参考: https://tendbcluster.com/ DDL 章节
USE test_db;
-- 示例1: 分片键为多个列
CREATE TABLE `spider_tb1` (
    `ip` varchar(100) not null,
    KEY `ix_ip` (`ip`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8;
-- 如果多个唯一健（含主键),shard_key只能是其中的共同部分；否则无法建表
create table `spider_tb2` (
    `id` int unsigned not null auto_increment,
    `code` tinyint unsigned not null,
    `name` char(20) not null,
    primary key (id),
    unique (id, name)
) comment = 'shard_key "id"';
-- 如果有多个唯一键,不指定shard_key, 默认会用唯一键的第一个字段作为分区key。但需保证分区key是每个唯一键的第一个字段，否则无法建表。
create table `spider_tb3` (c1 int primary key, c2 int, unique key t(c1, c2));
-- 如果多个普通索引，则必须指定shard_key（Tdbctl上作的限制）
create table `spider_tb4` (
    `id` int unsigned not null auto_increment,
    `code` tinyint unsigned not null,
    `name` char(20) not null,
    key a(id),
    key b(name)
) comment = 'shard_key "id"';
-- 如果只有一个唯一键（含主键),不指定shard_key, 默认会用唯一键的第一个字段作为分区key
create table t1(
    `inf_id` int(11) auto_increment not null,
    `name` varchar(50) not null,
    `sex` varchar(5) not null,
    `birthday` varchar(50) not null,
    primary key info(inf_id, sex)
);