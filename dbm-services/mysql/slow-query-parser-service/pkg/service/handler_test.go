package service

import "testing"

var sample = []string{
	"select a.ip, b.port from db_meta_machine a, db_meta_storageinstance b where a.cluster_type='tendbha' and a.access_layer='storage' and a.bk_host_id = b.machine_id",
	"select user,host from mysql.user where host like '%238'",
	"select count(*) from tb_mrgame_onlinecnt_0",
	"select b.bk_biz_id,b.ip,a.port,a.status from db_meta_storageinstance a, db_meta_machine b where a.machine_id = b.bk_host_id and b.ip in ('abcdefg', '123456')",
	"update db_meta_storageinstance set status='unavailable' where id in (16184,16183)",
	"show create table db_meta_module",
	"select * from db_meta_cluster where id = '1001399'",
	"alter table ha_agent_logs add index idx1(agent_ip, ip, port), drop index idx_ins",
	"insert into tb_instance_version_charset(ip, port, version, charset, engines, addr, update_at, create_at) values('1a250960b28', 20003, '5.5.24-tmysql-1.6-log', 'utf8mb4', 'InnoDB', '11150608:20003', now(), now())",
	"create table tb_instance_version_charset(version text, charset int, engines text)",
}

func BenchmarkParseQuery(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ParseQuery(sample[i%10])
	}
}
