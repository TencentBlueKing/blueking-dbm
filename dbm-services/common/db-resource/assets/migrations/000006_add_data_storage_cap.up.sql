ALTER TABLE tb_rp_detail
add column `total_data_storage_cap` int(11) DEFAULT 0 COMMENT '数据盘总容量'
after `total_storage_cap`;
ALTER TABLE tb_rp_detail_archive
add column `total_data_storage_cap` int(11) DEFAULT 0 COMMENT '数据盘总容量'
after `total_storage_cap`;