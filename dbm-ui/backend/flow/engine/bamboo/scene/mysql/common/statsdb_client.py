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
    "DBSIZE": """SELECT cluster_domain, database_name, MAX(database_size) as bytes
        FROM mysql_db_table_size
        WHERE cluster_domain = %s AND database_name IN (%s)
        AND dteventtimehour > DATE_ADD(NOW(), INTERVAL -1 DAY)
        GROUP BY cluster_domain, database_name;"""
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
