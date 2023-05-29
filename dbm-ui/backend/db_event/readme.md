
# 查询切换记录

GET: /switchqueue

{
    "name": "`get_switch_log`",
    "query_args": {
        "db_type": string
		"db_role": string
		.....
    }
}

{
    "code": 0,
    "message": "",
    "data": [
        {
            "uid": uint, 不展示，但是详情时需要用此查询
            "ip": string, 对应IP
            "port": int, 对应PORT
			"slave_ip", string, 对应Slave IP，返回可能为空
			"slave_port", string，对应Slave Port，返回可能为空
            "domain_name": string, 对应集群
            "app": string,对应业务
			"db_type": string,对应实例类型
			"db_role": string, 对应实例角色
            "switch_start_time": timestamp, 对应开始时间
            "switch_finished_time": timestamp,对应结束时间
			"confirm_check_time": string, 检测结束时间（目前页面没有建议加上）
			"switch_result": string, 对应切换结果
			"confirm_result": string, 对应切换原因
        }
    ]
}

# 查询切换日志

GET：/halogs

{
    "name": "`get_switch_log`",
    "query_args": {
        "ck_id": int
    }
}

{
    "code": 0,
    "message": "",
    "data": [
        {
            "uid": uint, 自增排序
            "ip": string, 对应IP
			"result", string
			"datetime", datetime,
			"content", string
        }
    ]
}