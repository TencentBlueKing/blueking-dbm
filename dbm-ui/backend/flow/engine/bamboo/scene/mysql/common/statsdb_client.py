import pymysql

from backend import env

# DBM StatsDB Doris数据库连接信息
STATSDB_DSN = {
    "user": env.DBM_STATSDB_USER,
    "password": env.DBM_STATSDB_PASSWORD,
    "address": env.DBM_STATSDB_URL,
    "database": env.DBM_STATSDB_NAME,
    "charset": "utf8",
}

DB_QUERY_TEMPLATE = {
    "DBSIZE": """select concat_ws('|',cluster_domain,database_name) as db,
    round(database_size/1024/1024/1024, 2) as gb, dteventtimehour from
    (select cluster_domain, database_name, database_size, dteventtimehour,
    row_number()over(partition by cluster_domain, database_name order by
    dteventtimehour desc) as desc_rn from mysql_db_table_size
    where (%s) AND dteventtimehour > DATE_ADD(NOW(), INTERVAL -3 DAY))
    as t1 where t1.desc_rn = 1;"""
}


class StatsDBClient:
    def __init__(self):
        """
        初始化 Doris 数据库客户端，使用全局常量 STATSDB_DSN 作为默认连接信息
        """
        dsn = STATSDB_DSN
        host, port = dsn["address"].split(":")
        self.connection = pymysql.connect(
            host=host,
            port=int(port),
            user=dsn["user"],
            password=dsn["password"],
            database=dsn["database"],
            charset=dsn.get("charset", "utf8"),
            autocommit=True,
        )

    def query(self, sql, args=None):
        """
        执行 SQL 查询并返回结果
        :param sql: SQL 查询语句
        :param args: 可选参数，SQL 占位参数
        :return: 查询结果列表（每行为一个字典）
        """
        with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, args)
            result = cursor.fetchall()
        return result

    def close(self):
        """
        关闭数据库连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def __del__(self):
        self.close()
