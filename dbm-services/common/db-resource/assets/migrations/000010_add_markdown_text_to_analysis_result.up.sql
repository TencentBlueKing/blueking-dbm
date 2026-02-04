ALTER TABLE `tb_rp_analysis_result`
ADD COLUMN `markdown_text` text COMMENT 'Markdown格式的分析结果'
AFTER `analysis_result`;