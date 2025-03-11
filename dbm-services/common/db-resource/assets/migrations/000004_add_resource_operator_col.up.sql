ALTER TABLE tb_rp_detail
add column `operator` char(64) not null default '' comment '资源导入者';
ALTER TABLE tb_rp_detail_archive
add column `operator` char(64) not null default '' comment '资源导入者';